/* --------------------------------------------------
   Lavi OSINT Manager - Frontend SPA (app.js)
   -------------------------------------------------- */

const API_BASE = window.location.origin;

// Estado Global da Aplicação
const state = {
    token: localStorage.getItem("lavi_admin_token") || null,
    currentTab: "dashboard-tab",
    bots: [],
    targets: []
};

// Seletores DOM Globais
const loginContainer = document.getElementById("login-container");
const passwordChangeContainer = document.getElementById("password-change-container");
const appContainer = document.getElementById("app-container");
const loginForm = document.getElementById("login-form");
const passwordChangeForm = document.getElementById("password-change-form");
const loginError = document.getElementById("login-error");
const passwordChangeError = document.getElementById("password-change-error");
const currentAdminUser = document.getElementById("current-admin-user");
const btnLogout = document.getElementById("btn-logout");

// --------------------------------------------------
// Funções Auxiliares de API
// --------------------------------------------------
async function apiRequest(endpoint, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...options.headers
    };
    
    if (state.token) {
        headers["Authorization"] = `Bearer ${state.token}`;
    }

    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, config);
        
        if (response.status === 401) {
            // Sessão expirada/não autorizada
            handleLogout();
            throw new Error("Sessão expirada. Faça login novamente.");
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Erro ao processar requisição.");
        }
        return data;
    } catch (error) {
        console.error(`Erro na requisição ${endpoint}:`, error);
        throw error;
    }
}

// --------------------------------------------------
// Autenticação & Inicialização
// --------------------------------------------------
async function initApp() {
    if (!state.token) {
        showLoginScreen();
        return;
    }

    try {
        const me = await apiRequest("/api/auth/me");
        currentAdminUser.textContent = me.username;
        
        if (me.must_change_password) {
            showPasswordChangeScreen();
        } else {
            showDashboardScreen();
        }
    } catch (e) {
        showLoginScreen();
    }
}

function showLoginScreen() {
    loginContainer.classList.remove("hidden");
    passwordChangeContainer.classList.add("hidden");
    appContainer.classList.add("hidden");
}

function showPasswordChangeScreen() {
    loginContainer.classList.add("hidden");
    passwordChangeContainer.classList.remove("hidden");
    appContainer.classList.add("hidden");
}

function showDashboardScreen() {
    loginContainer.classList.add("hidden");
    passwordChangeContainer.classList.add("hidden");
    appContainer.classList.remove("hidden");
    switchTab(state.currentTab);
    updateDashboardStats();
}

function handleLogout() {
    state.token = null;
    localStorage.removeItem("lavi_admin_token");
    showLoginScreen();
}

// Evento de Login
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.classList.add("hidden");
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
        const res = await apiRequest("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username, password })
        });
        
        state.token = res.access_token;
        localStorage.setItem("lavi_admin_token", state.token);
        
        if (res.must_change_password) {
            showPasswordChangeScreen();
        } else {
            showDashboardScreen();
        }
    } catch (err) {
        loginError.textContent = err.message;
        loginError.classList.remove("hidden");
    }
});

// Evento de Alteração de Senha
passwordChangeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    passwordChangeError.classList.add("hidden");
    const old_password = document.getElementById("old-password").value;
    const new_password = document.getElementById("new-password").value;

    try {
        await apiRequest("/api/auth/change-password", {
            method: "POST",
            body: JSON.stringify({ old_password, new_password })
        });
        showDashboardScreen();
    } catch (err) {
        passwordChangeError.textContent = err.message;
        passwordChangeError.classList.remove("hidden");
    }
});

btnLogout.addEventListener("click", handleLogout);

// --------------------------------------------------
// Navegação por Abas
// --------------------------------------------------
const navItems = document.querySelectorAll(".nav-item");
navItems.forEach(item => {
    item.addEventListener("click", (e) => {
        e.preventDefault();
        const tabId = item.getAttribute("data-tab");
        switchTab(tabId);
    });
});

function switchTab(tabId) {
    state.currentTab = tabId;
    
    // Altera classe ativa do menu
    navItems.forEach(item => {
        if (item.getAttribute("data-tab") === tabId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    // Exibe/oculta seções
    const tabContents = document.querySelectorAll(".tab-content");
    tabContents.forEach(content => {
        if (content.id === tabId) {
            content.classList.remove("hidden");
        } else {
            content.classList.add("hidden");
        }
    });

    // Carrega dados específicos da aba
    if (tabId === "dashboard-tab") {
        updateDashboardStats();
    } else if (tabId === "bots-tab") {
        loadBots();
    } else if (tabId === "targets-tab") {
        loadTargets();
    } else if (tabId === "posts-tab") {
        loadPostsTab();
    } else if (tabId === "logs-tab") {
        loadLogs();
    }
}

// --------------------------------------------------
// ABA: Dashboard
// --------------------------------------------------
async function updateDashboardStats() {
    try {
        const bots = await apiRequest("/api/bots");
        const targets = await apiRequest("/api/targets");
        
        // Conta bots ativos
        const activeBots = bots.filter(b => b.status === "ACTIVE").length;
        document.getElementById("stat-bots-count").textContent = activeBots;
        document.getElementById("stat-targets-count").textContent = targets.length;
        
        // Simulação simples de total de posts para a estatística
        const posts = await apiRequest("/api/search?q=a"); // Busca genérica
        document.getElementById("stat-posts-count").textContent = posts.length || 0;
    } catch (e) {
        console.error("Falha ao carregar estatísticas do dashboard", e);
    }
}

// --------------------------------------------------
// ABA: Bots
// --------------------------------------------------
async function loadBots() {
    const tbody = document.getElementById("bots-list-body");
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;">Carregando bots...</td></tr>`;

    try {
        state.bots = await apiRequest("/api/bots");
        tbody.innerHTML = "";

        if (state.bots.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;">Nenhum bot cadastrado.</td></tr>`;
            return;
        }

        state.bots.forEach(bot => {
            const statusClass = bot.status === "ACTIVE" ? "badge-success" : "badge-danger";
            const lastUsed = bot.last_used_at ? new Date(bot.last_used_at).toLocaleString("pt-BR") : "Nunca usado";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>@${bot.username}</strong></td>
                <td><span class="badge ${statusClass}">${bot.status}</span></td>
                <td>${lastUsed}</td>
                <td>
                    <button class="btn-action-delete" onclick="deleteBot('${bot.username}')">
                        <i class="fa-solid fa-trash-can"></i> Excluir
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--danger)">Erro ao carregar lista de bots.</td></tr>`;
    }
}

const botForm = document.getElementById("bot-create-form");
const botFeedback = document.getElementById("bot-action-feedback");

botForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    botFeedback.textContent = "Iniciando Playwright Headless em background. Aguarde o login do Instagram... (pode demorar até 20s)";
    botFeedback.classList.remove("hidden");
    const btnSubmit = document.getElementById("btn-submit-bot");
    btnSubmit.disabled = true;

    const username = document.getElementById("bot-username").value;
    const password = document.getElementById("bot-password").value;

    try {
        await apiRequest("/api/bots", {
            method: "POST",
            body: JSON.stringify({ username, password })
        });
        botFeedback.textContent = "Bot autenticado com sucesso!";
        botForm.reset();
        loadBots();
    } catch (err) {
        botFeedback.textContent = err.message;
    } finally {
        btnSubmit.disabled = false;
        setTimeout(() => botFeedback.classList.add("hidden"), 10000);
    }
});

async function deleteBot(username) {
    if (!confirm(`Deseja realmente remover o bot @${username}? A sessão local associada será excluída.`)) return;
    try {
        await apiRequest(`/api/bots/${username}`, { method: "DELETE" });
        loadBots();
    } catch (e) {
        alert(e.message);
    }
}

// --------------------------------------------------
// ABA: Alvos Monitorados (Targets)
// --------------------------------------------------
async function loadTargets() {
    const tbody = document.getElementById("targets-list-body");
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">Carregando alvos...</td></tr>`;

    try {
        state.targets = await apiRequest("/api/targets");
        tbody.innerHTML = "";

        if (state.targets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">Nenhum alvo de monitoramento cadastrado.</td></tr>`;
            return;
        }

        state.targets.forEach(target => {
            const lastScraped = target.last_scraped_at ? new Date(target.last_scraped_at).toLocaleString("pt-BR") : "Pendente";
            const activeBadge = target.is_active ? "badge-success" : "badge-danger";
            const activeText = target.is_active ? "Ativo" : "Inativo";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <strong>@${target.username}</strong>
                    <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">
                        Feed: ${target.download_feed ? 'Sim' : 'Não'} | Stories: ${target.download_stories ? 'Sim' : 'Não'}
                    </div>
                </td>
                <td>A cada ${target.check_frequency_hours}h</td>
                <td>${lastScraped}</td>
                <td>
                    <button class="btn-secondary-action" onclick="toggleTargetActive(${target.id}, ${target.is_active})">
                        <span class="badge ${activeBadge}">${activeText}</span>
                    </button>
                    <button class="btn-action-delete" onclick="deleteTarget(${target.id}, '${target.username}')">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </td>
                <td>
                    <div style="display:flex; gap:6px;">
                        <button class="btn-secondary-action" onclick="scrapeTargetManual(${target.id}, 'STORIES')">Stories</button>
                        <button class="btn-secondary-action" onclick="scrapeTargetManual(${target.id}, 'FEED')">Feed</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--danger)">Erro ao carregar lista de alvos.</td></tr>`;
    }
}

const targetForm = document.getElementById("target-create-form");
targetForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("target-username").value;
    const download_feed = document.getElementById("target-feed").checked ? 1 : 0;
    const download_stories = document.getElementById("target-stories").checked ? 1 : 0;
    const download_comments = document.getElementById("target-comments").checked ? 1 : 0;
    const check_frequency_hours = parseInt(document.getElementById("target-freq").value);

    try {
        await apiRequest("/api/targets", {
            method: "POST",
            body: JSON.stringify({
                username,
                download_feed,
                download_stories,
                download_comments,
                check_frequency_hours
            })
        });
        targetForm.reset();
        loadTargets();
    } catch (err) {
        alert(err.message);
    }
});

async function toggleTargetActive(id, currentStatus) {
    const is_active = currentStatus ? 0 : 1;
    try {
        await apiRequest(`/api/targets/${id}`, {
            method: "PUT",
            body: JSON.stringify({ is_active })
        });
        loadTargets();
    } catch (e) {
        alert(e.message);
    }
}

async function deleteTarget(id, username) {
    if (!confirm(`Remover @${username} do monitoramento e excluir seus posts indexados?`)) return;
    try {
        await apiRequest(`/api/targets/${id}`, { method: "DELETE" });
        loadTargets();
    } catch (e) {
        alert(e.message);
    }
}

async function scrapeTargetManual(id, type) {
    try {
        const res = await apiRequest(`/api/targets/${id}/scrape?job_type=${type}`, { method: "POST" });
        alert(res.message);
    } catch (e) {
        alert(e.message);
    }
}

// --------------------------------------------------
// ABA: Dados Coletados
// --------------------------------------------------
const btnFilterPosts = document.getElementById("btn-filter-posts");
const filterPostTarget = document.getElementById("filter-post-target");
const filterPostType = document.getElementById("filter-post-type");
const postsListContainer = document.getElementById("posts-list-container");

if (btnFilterPosts) {
    btnFilterPosts.addEventListener("click", loadPostsTab);
}

async function loadPostsTab() {
    if (!postsListContainer) return;
    postsListContainer.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">Carregando dados coletados...</p>`;
    
    try {
        // Carrega alvos para o filtro se o dropdown estiver vazio (exceto opção "Todos")
        if (filterPostTarget && filterPostTarget.options.length <= 1) {
            const targets = await apiRequest("/api/targets");
            filterPostTarget.innerHTML = '<option value="">Todos os Alvos</option>';
            targets.forEach(t => {
                const opt = document.createElement("option");
                opt.value = t.id;
                opt.textContent = `@${t.username}`;
                filterPostTarget.appendChild(opt);
            });
        }

        // Constrói query params
        const targetId = filterPostTarget ? filterPostTarget.value : "";
        const postType = filterPostType ? filterPostType.value : "";
        
        let url = "/api/posts?limit=50";
        if (targetId) url += `&target_id=${targetId}`;
        if (postType) url += `&post_type=${postType}`;
        
        const posts = await apiRequest(url);
        postsListContainer.innerHTML = "";
        
        if (posts.length === 0) {
            postsListContainer.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">Nenhum post ou mídia coletada encontrada com estes filtros.</p>`;
            return;
        }
        
        posts.forEach(post => {
            const card = document.createElement("div");
            card.className = "result-card";
            
            const relativeMediaSrc = post.local_path.replace("data/downloads/", "/media/");
            const mediaTypeIcon = post.post_type === "VIDEO" ? '<i class="fa-solid fa-play"></i>' : '<i class="fa-solid fa-image"></i>';
            const dateStr = new Date(post.taken_at).toLocaleDateString("pt-BR");
            
            card.innerHTML = `
                <div class="result-media-preview">
                    ${post.post_type === 'VIDEO' 
                        ? `<video src="${relativeMediaSrc}" muted></video>` 
                        : `<img src="${relativeMediaSrc}" alt="Mídia">`}
                    <div class="media-type-badge">${mediaTypeIcon} ${post.post_type}</div>
                </div>
                <div class="result-info">
                    <div class="result-author">@${post.target_username}</div>
                    <div class="result-date">${dateStr}</div>
                    <div class="result-caption">${post.caption || 'Sem legenda.'}</div>
                </div>
            `;
            
            card.addEventListener("click", () => openPostModal(post, relativeMediaSrc));
            postsListContainer.appendChild(card);
        });
    } catch (e) {
        postsListContainer.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--danger);">Falha ao carregar dados coletados: ${e.message}</p>`;
    }
}

// --------------------------------------------------
// ABA: Busca FTS5
// --------------------------------------------------
const btnSearch = document.getElementById("btn-search");
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results-container");

btnSearch.addEventListener("click", performSearch);
searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") performSearch();
});

async function performSearch() {
    const q = searchInput.value.strip ? searchInput.value.strip() : searchInput.value.trim();
    if (q.length < 2) {
        searchResults.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">Digite ao menos 2 caracteres para pesquisar.</p>`;
        return;
    }

    searchResults.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">Buscando em FTS5 virtual table...</p>`;

    try {
        const results = await apiRequest(`/api/search?q=${encodeURIComponent(q)}`);
        searchResults.innerHTML = "";

        if (results.length === 0) {
            searchResults.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">Nenhum resultado encontrado.</p>`;
            return;
        }

        results.forEach(post => {
            const card = document.createElement("div");
            card.className = "result-card";
            
            // Corrige o caminho local da mídia para ler pela rota /media
            // local_path no banco aponta para something like 'data/downloads/@target/feed/file.jpg'
            const relativeMediaSrc = post.local_path.replace("data/downloads/", "/media/");
            
            const mediaTypeIcon = post.post_type === "VIDEO" ? '<i class="fa-solid fa-play"></i>' : '<i class="fa-solid fa-image"></i>';
            const dateStr = new Date(post.taken_at).toLocaleDateString("pt-BR");

            card.innerHTML = `
                <div class="result-media-preview">
                    ${post.post_type === 'VIDEO' 
                        ? `<video src="${relativeMediaSrc}" muted></video>` 
                        : `<img src="${relativeMediaSrc}" alt="Midia">`}
                    <div class="media-type-badge">${mediaTypeIcon} ${post.post_type}</div>
                </div>
                <div class="result-info">
                    <div class="result-author">@${post.target_username}</div>
                    <div class="result-date">${dateStr}</div>
                    <div class="result-caption">${post.caption || 'Sem legenda.'}</div>
                </div>
            `;
            
            // Evento para abrir modal detalhado ao clicar no card
            card.addEventListener("click", () => openPostModal(post, relativeMediaSrc));
            searchResults.appendChild(card);
        });
    } catch (e) {
        searchResults.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color:var(--danger);">Falha ao realizar busca.</p>`;
    }
}

// --------------------------------------------------
// Modal Detalhes do Post
// --------------------------------------------------
const postModal = document.getElementById("post-modal");
const closeModal = document.querySelector(".close-modal");
const modalMediaContainer = document.getElementById("modal-media-container");
const modalTargetUsername = document.getElementById("modal-target-username");
const modalPostDate = document.getElementById("modal-post-date");
const modalPostCaption = document.getElementById("modal-post-caption");
const modalPostComments = document.getElementById("modal-post-comments");

function openPostModal(post, mediaSrc) {
    modalMediaContainer.innerHTML = "";
    if (post.post_type === "VIDEO") {
        const video = document.createElement("video");
        video.src = mediaSrc;
        video.controls = true;
        video.autoplay = true;
        modalMediaContainer.appendChild(video);
    } else {
        const img = document.createElement("img");
        img.src = mediaSrc;
        modalMediaContainer.appendChild(img);
    }

    modalTargetUsername.textContent = `@${post.target_username}`;
    modalPostDate.textContent = new Date(post.taken_at).toLocaleString("pt-BR");
    modalPostCaption.textContent = post.caption || "Sem legenda.";
    modalPostComments.textContent = post.comments_sample || "Nenhum comentário ou engajamento textual indexado.";

    postModal.classList.remove("hidden");
}

closeModal.addEventListener("click", () => {
    postModal.classList.add("hidden");
    modalMediaContainer.innerHTML = ""; // Para parar execução de vídeo em background
});

window.addEventListener("click", (e) => {
    if (e.target === postModal) {
        postModal.classList.add("hidden");
        modalMediaContainer.innerHTML = "";
    }
});

// --------------------------------------------------
// ABA: Logs
// --------------------------------------------------
const btnRefreshLogs = document.getElementById("btn-refresh-logs");
const terminalOutput = document.getElementById("terminal-output");

btnRefreshLogs.addEventListener("click", loadLogs);

async function loadLogs() {
    terminalOutput.textContent = "Carregando logs operacionais em tempo real...";
    try {
        const res = await apiRequest("/api/logs");
        terminalOutput.textContent = res.logs || "Nenhum evento registrado no crawler.log ainda.";
        
        // Auto-scroll do terminal para o fim do log
        const terminalBody = document.querySelector(".terminal-body");
        terminalBody.scrollTop = terminalBody.scrollHeight;
    } catch (e) {
        terminalOutput.textContent = "Falha ao ler o arquivo de logs.";
    }
}

// Inicializa a aplicação ao carregar
window.addEventListener("DOMContentLoaded", initApp);
