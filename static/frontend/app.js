(function () {
  const DEFAULT_CODE = "a, b = map(int, input().split())\nprint(a + b)\n";
  const state = {
    accessToken: localStorage.getItem("meadowcode.access") || "",
    refreshToken: localStorage.getItem("meadowcode.refresh") || "",
    user: null,
    problem: null,
    nextPage: null,
    previousPage: null,
    difficulty: "",
    searchTimer: null,
    pollTimer: null
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindAuth();
    syncSession();

    const page = document.body.dataset.page;
    if (page === "problem-list") initProblemList();
    if (page === "problem-detail") initProblemDetail();
  });

  function bindAuth() {
    const form = document.getElementById("auth-form");
    const logoutButton = document.getElementById("logout-button");

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const username = document.getElementById("auth-username").value.trim();
      const password = document.getElementById("auth-password").value;

      if (!username || !password) {
        toast("Username and password are required.");
        return;
      }

      try {
        const data = await api("/api/auth/token/", {
          method: "POST",
          auth: false,
          body: { username, password }
        });
        state.accessToken = data.access;
        state.refreshToken = data.refresh;
        localStorage.setItem("meadowcode.access", state.accessToken);
        localStorage.setItem("meadowcode.refresh", state.refreshToken);
        await syncSession();
        toast("Logged in.");
      } catch (error) {
        toast(error.message);
      }
    });

    logoutButton?.addEventListener("click", () => {
      state.accessToken = "";
      state.refreshToken = "";
      state.user = null;
      localStorage.removeItem("meadowcode.access");
      localStorage.removeItem("meadowcode.refresh");
      renderSession();
      toast("Logged out.");
    });
  }

  async function syncSession() {
    if (!state.accessToken) {
      renderSession();
      return;
    }

    try {
      state.user = await api("/api/accounts/me/");
    } catch (error) {
      state.accessToken = "";
      state.refreshToken = "";
      localStorage.removeItem("meadowcode.access");
      localStorage.removeItem("meadowcode.refresh");
    }

    renderSession();
  }

  function renderSession() {
    const form = document.getElementById("auth-form");
    const session = document.getElementById("session");
    const sessionName = document.getElementById("session-name");

    if (!form || !session || !sessionName) return;

    if (state.user) {
      form.hidden = true;
      session.hidden = false;
      sessionName.textContent = state.user.username;
      return;
    }

    form.hidden = false;
    session.hidden = true;
    sessionName.textContent = "";
  }

  function initProblemList() {
    const searchInput = document.getElementById("problem-search");
    const difficultyFilter = document.getElementById("difficulty-filter");
    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");

    searchInput?.addEventListener("input", () => {
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(() => loadProblems(), 250);
    });

    difficultyFilter?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-difficulty]");
      if (!button) return;

      state.difficulty = button.dataset.difficulty;
      difficultyFilter.querySelectorAll(".segment-button").forEach((item) => {
        item.classList.toggle("is-active", item === button);
      });
      loadProblems();
    });

    prevButton?.addEventListener("click", () => {
      if (state.previousPage) loadProblems(state.previousPage);
    });

    nextButton?.addEventListener("click", () => {
      if (state.nextPage) loadProblems(state.nextPage);
    });

    loadProblems();
  }

  async function loadProblems(url) {
    const searchValue = document.getElementById("problem-search")?.value.trim() || "";
    const endpoint = url || buildProblemListUrl(searchValue, state.difficulty);

    setProblemCount("Loading...");

    try {
      const data = await api(endpoint, { auth: false, absolute: Boolean(url) });
      const results = Array.isArray(data.results) ? data.results : data;
      state.nextPage = data.next || null;
      state.previousPage = data.previous || null;
      renderProblemList(results, data.count);
    } catch (error) {
      renderProblemList([], 0);
      toast(error.message);
    }
  }

  function buildProblemListUrl(searchValue, difficulty) {
    const params = new URLSearchParams();
    params.set("ordering", "title");
    if (searchValue) params.set("search", searchValue);
    if (difficulty) params.set("difficulty", difficulty);
    return `/api/problems/?${params.toString()}`;
  }

  function renderProblemList(problems, count) {
    const tbody = document.getElementById("problem-list");
    const empty = document.getElementById("problem-empty");
    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");

    if (!tbody || !empty) return;

    tbody.replaceChildren();
    empty.hidden = problems.length > 0;

    problems.forEach((problem) => {
      const row = document.createElement("tr");
      row.append(
        tableCell(problemLink(problem)),
        tableCell(difficultyPill(problem.difficulty)),
        tableCell(tagList(problem.tags || [])),
        tableCell(limitText(problem))
      );
      tbody.append(row);
    });

    setProblemCount(`${count ?? problems.length} problems`);
    if (prevButton) prevButton.disabled = !state.previousPage;
    if (nextButton) nextButton.disabled = !state.nextPage;
  }

  function problemLink(problem) {
    const link = document.createElement("a");
    link.className = "problem-link";
    link.href = `/problems/${problem.slug}/`;
    link.textContent = problem.title;
    return link;
  }

  function setProblemCount(text) {
    const count = document.getElementById("problem-count");
    if (count) count.textContent = text;
  }

  function initProblemDetail() {
    const editor = document.getElementById("code-editor");
    const submitButton = document.getElementById("submit-code");
    const resetButton = document.getElementById("reset-code");

    if (editor) editor.value = localStorage.getItem("meadowcode.code") || DEFAULT_CODE;
    editor?.addEventListener("input", () => {
      localStorage.setItem("meadowcode.code", editor.value);
    });

    resetButton?.addEventListener("click", () => {
      if (!editor) return;
      editor.value = DEFAULT_CODE;
      localStorage.setItem("meadowcode.code", editor.value);
      editor.focus();
    });

    submitButton?.addEventListener("click", submitSolution);
    loadProblemDetail();
  }

  async function loadProblemDetail() {
    const slug = document.body.dataset.problemSlug;

    try {
      state.problem = await api(`/api/problems/${slug}/`, { auth: false });
      renderProblemDetail(state.problem);
    } catch (error) {
      setText("problem-title", "Problem not found");
      toast(error.message);
    }
  }

  function renderProblemDetail(problem) {
    setText("problem-title", problem.title);

    const difficulty = document.getElementById("problem-difficulty");
    if (difficulty) {
      difficulty.replaceWith(difficultyPill(problem.difficulty));
      document.querySelector(".problem-heading .difficulty-pill").id = "problem-difficulty";
    }

    const tags = document.getElementById("problem-tags");
    if (tags) {
      tags.replaceChildren(...(problem.tags || []).map(tagPill));
    }

    setPreformatted("problem-statement", problem.statement);
    setOptionalBlock("examples-block", "problem-examples", problem.examples, true);
    setOptionalBlock("constraints-block", "problem-constraints", problem.constraints, false);
    renderSamples(problem.samples || []);
  }

  function renderSamples(samples) {
    const block = document.getElementById("samples-block");
    const container = document.getElementById("problem-samples");
    if (!block || !container) return;

    container.replaceChildren();
    block.hidden = samples.length === 0;

    samples.forEach((sample, index) => {
      const wrapper = document.createElement("div");
      wrapper.className = "content-block";

      const title = document.createElement("h2");
      title.textContent = `Sample ${index + 1}`;

      const grid = document.createElement("div");
      grid.className = "sample-grid";
      grid.append(sampleBlock("Input", sample.input_data), sampleBlock("Expected", sample.expected_output));

      wrapper.append(title, grid);
      container.append(wrapper);
    });
  }

  function sampleBlock(title, value) {
    const wrapper = document.createElement("div");
    const label = document.createElement("div");
    const pre = document.createElement("pre");

    label.className = "sample-title";
    label.textContent = title;
    pre.className = "code-block";
    pre.textContent = value || "";

    wrapper.append(label, pre);
    return wrapper;
  }

  async function submitSolution() {
    if (!state.accessToken) {
      toast("Login required.");
      return;
    }

    if (!state.problem) {
      toast("Problem is still loading.");
      return;
    }

    const editor = document.getElementById("code-editor");
    const code = editor?.value || "";
    if (!code.trim()) {
      toast("Code is empty.");
      return;
    }

    setSubmission("pending", "Submitting...");

    try {
      const submission = await api("/api/submissions/", {
        method: "POST",
        body: {
          problem: state.problem.id,
          language: "python",
          code
        }
      });
      setSubmission(submission.status, submission.verdict_message || "Queued.");
      pollSubmission(submission.id);
    } catch (error) {
      setSubmission("error", error.message);
      toast(error.message);
    }
  }

  function pollSubmission(id) {
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(async () => {
      try {
        const submission = await api(`/api/submissions/${id}/`);
        setSubmission(submission.status, submission.verdict_message || "Running...");

        if (!["pending", "running"].includes(submission.status)) {
          clearInterval(state.pollTimer);
        }
      } catch (error) {
        clearInterval(state.pollTimer);
        setSubmission("error", error.message);
      }
    }, 1400);
  }

  function setSubmission(status, message) {
    setText("submission-status", humanStatus(status));
    setText("submission-message", message || "");
  }

  async function api(path, options = {}) {
    const response = await rawApi(path, options);

    if (response.status === 401 && options.auth !== false && state.refreshToken) {
      const refreshed = await refreshToken();
      if (refreshed) return api(path, options);
    }

    if (!response.ok) {
      throw new Error(await responseMessage(response));
    }

    if (response.status === 204) return null;
    return response.json();
  }

  function rawApi(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    if (options.auth !== false && state.accessToken) {
      headers.set("Authorization", `Bearer ${state.accessToken}`);
    }

    return fetch(options.absolute ? path : path, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined
    });
  }

  async function refreshToken() {
    try {
      const response = await rawApi("/api/auth/token/refresh/", {
        method: "POST",
        auth: false,
        body: { refresh: state.refreshToken }
      });

      if (!response.ok) return false;
      const data = await response.json();
      state.accessToken = data.access;
      localStorage.setItem("meadowcode.access", state.accessToken);
      return true;
    } catch (error) {
      return false;
    }
  }

  async function responseMessage(response) {
    try {
      const data = await response.json();
      if (typeof data.detail === "string") return data.detail;
      return JSON.stringify(data);
    } catch (error) {
      return `${response.status} ${response.statusText}`;
    }
  }

  function tableCell(content) {
    const cell = document.createElement("td");
    if (content instanceof Node) {
      cell.append(content);
    } else {
      cell.textContent = content || "";
    }
    return cell;
  }

  function difficultyPill(value) {
    const pill = document.createElement("span");
    const difficulty = value || "unknown";
    pill.className = `difficulty-pill difficulty-${difficulty}`;
    pill.textContent = humanStatus(difficulty);
    return pill;
  }

  function tagList(tags) {
    const list = document.createElement("div");
    list.className = "tag-list";
    if (!tags.length) {
      list.textContent = "-";
      return list;
    }
    tags.forEach((tag) => list.append(tagPill(tag)));
    return list;
  }

  function tagPill(tag) {
    const pill = document.createElement("span");
    pill.className = "tag-pill";
    pill.textContent = tag.name || tag.slug || tag;
    return pill;
  }

  function limitText(problem) {
    return `${problem.time_limit_ms} ms / ${problem.memory_limit_mb} MB`;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || "";
  }

  function setPreformatted(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || "";
  }

  function setOptionalBlock(blockId, contentId, value, isPre) {
    const block = document.getElementById(blockId);
    if (!block) return;
    block.hidden = !value;
    if (isPre) setText(contentId, value);
    else setPreformatted(contentId, value);
  }

  function humanStatus(value) {
    if (!value) return "";
    return String(value)
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function toast(message) {
    const element = document.getElementById("toast");
    if (!element) return;

    element.textContent = message;
    element.hidden = false;
    clearTimeout(element.dataset.timer);
    element.dataset.timer = setTimeout(() => {
      element.hidden = true;
    }, 3600);
  }
})();
