(function () {
  const state = {
    accessToken: localStorage.getItem("meadowcode.access") || "",
    refreshToken: localStorage.getItem("meadowcode.refresh") || "",
    user: null,
    problem: null,
    nextPage: null,
    previousPage: null,
    difficulty: "",
    searchTimer: null,
    pollTimer: null,
    editorStorageKey: "",
    starterCode: ""
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
        if (document.body.dataset.page === "problem-list") loadProblems();
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
      if (document.body.dataset.page === "problem-list") loadProblems();
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
      sessionName.textContent = `${state.user.username} · ${state.user.solved_count} solved`;
      updateDiscussionAuthState();
      updateSubmissionHistoryState();
      return;
    }

    form.hidden = false;
    session.hidden = true;
    sessionName.textContent = "";
    updateDiscussionAuthState();
    updateSubmissionHistoryState();
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
      const data = await api(endpoint, { absolute: Boolean(url) });
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
        tableCell(solvedMark(problem.is_solved)),
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

  function solvedMark(isSolved) {
    if (!isSolved) return "-";

    const mark = makeElement("span", "solved-mark", "Solved");
    mark.setAttribute("aria-label", "Solved");
    mark.title = "Solved";
    return mark;
  }

  function setProblemCount(text) {
    const count = document.getElementById("problem-count");
    if (count) count.textContent = text;
  }

  function initProblemDetail() {
    const editor = document.getElementById("code-editor");
    const submitButton = document.getElementById("submit-code");
    const resetButton = document.getElementById("reset-code");
    const threadForm = document.getElementById("thread-form");
    const discussionList = document.getElementById("discussion-list");
    const submissionHistory = document.getElementById("submission-history-list");
    const detailDialog = document.getElementById("submission-detail-dialog");
    const detailClose = document.getElementById("submission-detail-close");

    if (editor) editor.value = "# Loading problem...\n";
    editor?.addEventListener("input", () => {
      if (state.editorStorageKey) {
        localStorage.setItem(state.editorStorageKey, editor.value);
      }
    });
    editor?.addEventListener("keydown", handleEditorTab);

    resetButton?.addEventListener("click", () => {
      if (!editor) return;
      editor.value = state.starterCode;
      if (state.editorStorageKey) {
        localStorage.setItem(state.editorStorageKey, editor.value);
      }
      editor.focus();
    });

    submitButton?.addEventListener("click", submitSolution);
    threadForm?.addEventListener("submit", createDiscussionThread);
    discussionList?.addEventListener("click", handleDiscussionClick);
    discussionList?.addEventListener("submit", createDiscussionComment);
    submissionHistory?.addEventListener("click", openSubmissionDetails);
    detailClose?.addEventListener("click", () => detailDialog?.close());
    detailDialog?.addEventListener("click", (event) => {
      if (event.target === detailDialog) detailDialog.close();
    });
    updateDiscussionAuthState();
    updateSubmissionHistoryState();
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
    initializeEditor(problem);
    loadDiscussions(problem.id);
    updateSubmissionHistoryState();
  }

  function initializeEditor(problem) {
    const editor = document.getElementById("code-editor");
    const entryPoint = document.getElementById("entry-point");
    if (!editor) return;

    state.editorStorageKey = `meadowcode.code.${problem.slug}`;
    state.starterCode = starterCodeFor(problem);
    editor.value = localStorage.getItem(state.editorStorageKey) || state.starterCode;

    if (entryPoint) {
      entryPoint.textContent = `\u00b7 ${problem.function_name}(${problem.function_arguments || ""})`;
    }
  }

  function starterCodeFor(problem) {
    if (problem.starter_code?.trim()) return problem.starter_code;
    return `def ${problem.function_name || "solve"}(${problem.function_arguments || ""}):\n    pass\n`;
  }

  function updateDiscussionAuthState() {
    const threadForm = document.getElementById("thread-form");
    if (!threadForm) return;

    const canPost = Boolean(state.user);
    threadForm.querySelectorAll("input, textarea, button").forEach((control) => {
      control.disabled = !canPost;
    });

    const note = document.getElementById("discussion-login-note");
    if (note) note.hidden = canPost;

    document.querySelectorAll(".comment-form textarea, .comment-form button").forEach((control) => {
      control.disabled = !canPost;
    });
  }

  async function loadDiscussions(problemId) {
    const list = document.getElementById("discussion-list");
    if (!list) return;

    list.replaceChildren(makeElement("div", "discussion-loading", "Loading discussions..."));

    try {
      const data = await api(
        `/api/discussions/threads/?problem=${problemId}&ordering=-created_at`,
        { auth: false }
      );
      const threads = collectionResults(data);
      renderDiscussions(threads, data.count ?? threads.length);
    } catch (error) {
      list.replaceChildren(makeElement("div", "discussion-empty", error.message));
    }
  }

  function renderDiscussions(threads, count) {
    const list = document.getElementById("discussion-list");
    const countElement = document.getElementById("discussion-count");
    if (!list) return;

    if (countElement) countElement.textContent = String(count);
    list.replaceChildren();

    if (!threads.length) {
      list.append(makeElement("div", "discussion-empty", "No discussions yet."));
      return;
    }

    threads.forEach((thread) => list.append(createDiscussionElement(thread)));
    updateDiscussionAuthState();
  }

  function createDiscussionElement(thread) {
    const article = makeElement("article", "discussion-item");
    article.dataset.threadId = thread.id;

    const header = makeElement("div", "discussion-item-header");
    const title = makeElement("h3", "discussion-title", thread.title);
    const meta = makeElement(
      "div",
      "discussion-meta",
      `${thread.user} · ${formatDate(thread.created_at)}`
    );
    header.append(title, meta);

    const body = makeElement("div", "discussion-body", thread.body);
    const toggle = makeElement(
      "button",
      "discussion-toggle",
      `Comments (${thread.comments_count || 0})`
    );
    toggle.type = "button";
    toggle.dataset.commentsToggle = String(thread.id);
    toggle.setAttribute("aria-expanded", "false");

    const commentsPanel = makeElement("div", "comments-panel");
    commentsPanel.hidden = true;
    commentsPanel.dataset.threadId = String(thread.id);

    const commentsList = makeElement("div", "comments-list");
    const commentForm = makeElement("form", "comment-form");
    commentForm.dataset.threadId = String(thread.id);

    const textarea = makeElement("textarea", "input comment-textarea");
    textarea.name = "body";
    textarea.placeholder = "Write a comment";
    textarea.required = true;

    const submit = makeElement("button", "button button-primary", "Comment");
    submit.type = "submit";
    commentForm.append(textarea, submit);
    commentsPanel.append(commentsList, commentForm);

    article.append(header, body, toggle, commentsPanel);
    return article;
  }

  async function handleDiscussionClick(event) {
    const toggle = event.target.closest("[data-comments-toggle]");
    if (!toggle) return;

    const article = toggle.closest(".discussion-item");
    const panel = article?.querySelector(".comments-panel");
    if (!panel) return;

    const shouldOpen = panel.hidden;
    panel.hidden = !shouldOpen;
    toggle.setAttribute("aria-expanded", String(shouldOpen));

    if (shouldOpen && panel.dataset.loaded !== "true") {
      await loadComments(toggle.dataset.commentsToggle, panel);
    }
  }

  async function loadComments(threadId, panel) {
    const list = panel.querySelector(".comments-list");
    if (!list) return;

    list.replaceChildren(makeElement("div", "comment-loading", "Loading comments..."));

    try {
      const data = await api(
        `/api/discussions/comments/?thread=${threadId}&ordering=created_at`,
        { auth: false }
      );
      const comments = collectionResults(data);
      list.replaceChildren();

      if (!comments.length) {
        list.append(makeElement("div", "comment-empty", "No comments yet."));
      } else {
        comments.forEach((comment) => list.append(createCommentElement(comment)));
      }

      const count = data.count ?? comments.length;
      const toggle = panel.closest(".discussion-item")?.querySelector(".discussion-toggle");
      if (toggle) toggle.textContent = `Comments (${count})`;
      panel.dataset.loaded = "true";
      updateDiscussionAuthState();
    } catch (error) {
      list.replaceChildren(makeElement("div", "comment-empty", error.message));
    }
  }

  function createCommentElement(comment) {
    const item = makeElement("div", "comment-item");
    const meta = makeElement(
      "div",
      "comment-meta",
      `${comment.user} · ${formatDate(comment.created_at)}`
    );
    const body = makeElement("div", "comment-body", comment.body);
    item.append(meta, body);
    return item;
  }

  async function createDiscussionThread(event) {
    event.preventDefault();
    if (!state.user || !state.problem) {
      toast("Login required.");
      return;
    }

    const form = event.currentTarget;
    const title = form.elements.title.value.trim();
    const body = form.elements.body.value.trim();
    if (!title || !body) return;

    try {
      await api("/api/discussions/threads/", {
        method: "POST",
        body: { problem: state.problem.id, title, body }
      });
      form.reset();
      await loadDiscussions(state.problem.id);
      toast("Discussion posted.");
    } catch (error) {
      toast(error.message);
    }
  }

  async function createDiscussionComment(event) {
    const form = event.target.closest(".comment-form");
    if (!form) return;
    event.preventDefault();

    if (!state.user) {
      toast("Login required.");
      return;
    }

    const body = form.elements.body.value.trim();
    if (!body) return;

    try {
      await api("/api/discussions/comments/", {
        method: "POST",
        body: { thread: Number(form.dataset.threadId), body }
      });
      form.reset();
      const panel = form.closest(".comments-panel");
      if (panel) await loadComments(form.dataset.threadId, panel);
      toast("Comment posted.");
    } catch (error) {
      toast(error.message);
    }
  }

  function collectionResults(data) {
    return Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
  }

  function makeElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function formatDate(value) {
    if (!value) return "";
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short"
    }).format(new Date(value));
  }

  function handleEditorTab(event) {
    if (event.key !== "Tab") return;

    event.preventDefault();
    const editor = event.currentTarget;
    const indent = "    ";
    const start = editor.selectionStart;
    const end = editor.selectionEnd;

    if (!event.shiftKey && start === end) {
      editor.setRangeText(indent, start, end, "end");
      editor.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }

    const value = editor.value;
    const lineStart = value.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
    const effectiveEnd = end > start && value[end - 1] === "\n" ? end - 1 : end;
    const nextLineBreak = value.indexOf("\n", effectiveEnd);
    const lineEnd = nextLineBreak === -1 ? value.length : nextLineBreak;
    const lines = value.slice(lineStart, lineEnd).split("\n");

    if (event.shiftKey) {
      let totalRemoved = 0;
      let firstLineRemoved = 0;
      const replacement = lines.map((line, index) => {
        const match = line.match(/^(?: {1,4}|\t)/);
        const removed = match ? match[0].length : 0;
        if (index === 0) firstLineRemoved = removed;
        totalRemoved += removed;
        return line.slice(removed);
      }).join("\n");

      editor.setRangeText(replacement, lineStart, lineEnd, "select");
      editor.selectionStart = Math.max(lineStart, start - firstLineRemoved);
      editor.selectionEnd = Math.max(editor.selectionStart, end - totalRemoved);
    } else {
      const replacement = lines.map((line) => `${indent}${line}`).join("\n");
      editor.setRangeText(replacement, lineStart, lineEnd, "select");
      editor.selectionStart = start + indent.length;
      editor.selectionEnd = end + indent.length * lines.length;
    }

    editor.dispatchEvent(new Event("input", { bubbles: true }));
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

  function updateSubmissionHistoryState() {
    const loginMessage = document.getElementById("submission-history-login");
    const list = document.getElementById("submission-history-list");
    const count = document.getElementById("submission-history-count");
    if (!loginMessage || !list) return;

    const canView = Boolean(state.user);
    loginMessage.hidden = canView;
    list.hidden = !canView;

    if (!canView) {
      list.replaceChildren();
      if (count) count.textContent = "";
      return;
    }

    if (state.problem) loadSubmissionHistory(state.problem.id);
  }

  async function loadSubmissionHistory(problemId) {
    const list = document.getElementById("submission-history-list");
    if (!list || !state.user) return;

    list.replaceChildren(makeElement("div", "submission-history-empty", "Loading submissions..."));

    try {
      const data = await api(
        `/api/submissions/?problem=${problemId}&ordering=-created_at`
      );
      const submissions = collectionResults(data);
      renderSubmissionHistory(submissions, data.count ?? submissions.length);
    } catch (error) {
      list.replaceChildren(makeElement("div", "submission-history-empty", error.message));
    }
  }

  function renderSubmissionHistory(submissions, count) {
    const list = document.getElementById("submission-history-list");
    const countElement = document.getElementById("submission-history-count");
    if (!list) return;

    if (countElement) countElement.textContent = String(count);
    list.replaceChildren();

    if (!submissions.length) {
      list.append(makeElement("div", "submission-history-empty", "No submissions yet."));
      return;
    }

    submissions.forEach((submission) => {
      const item = makeElement("button", "submission-history-item");
      item.type = "button";
      item.dataset.submissionId = String(submission.id);

      const id = makeElement("strong", "submission-history-id", `#${submission.id}`);
      const status = submissionStatusPill(submission.status);
      const language = makeElement("span", "submission-history-language", humanStatus(submission.language));
      const runtime = makeElement(
        "span",
        "submission-history-runtime",
        submission.runtime_ms === null ? "-" : `${submission.runtime_ms} ms`
      );
      const created = makeElement(
        "span",
        "submission-history-created",
        formatDate(submission.created_at)
      );

      item.append(id, status, language, runtime, created);
      list.append(item);
    });
  }

  function submissionStatusPill(status) {
    const pill = makeElement("span", `status-pill status-${status}`, humanStatus(status));
    return pill;
  }

  async function openSubmissionDetails(event) {
    const item = event.target.closest("[data-submission-id]");
    if (!item) return;

    const dialog = document.getElementById("submission-detail-dialog");
    if (!dialog) return;

    setText("submission-detail-title", `#${item.dataset.submissionId}`);
    setText("submission-detail-status", "Loading...");
    setText("submission-detail-message", "");
    setText("submission-detail-code", "");

    if (!dialog.open) dialog.showModal();

    try {
      const submission = await api(`/api/submissions/${item.dataset.submissionId}/`);
      renderSubmissionDetails(submission);
    } catch (error) {
      setText("submission-detail-status", "Error");
      setText("submission-detail-message", error.message);
    }
  }

  function renderSubmissionDetails(submission) {
    setText("submission-detail-title", `#${submission.id} · ${submission.problem_title}`);
    setText("submission-detail-status", humanStatus(submission.status));
    setText("submission-detail-language", humanStatus(submission.language));
    setText(
      "submission-detail-runtime",
      submission.runtime_ms === null ? "-" : `${submission.runtime_ms} ms`
    );
    setText(
      "submission-detail-memory",
      submission.memory_kb === null ? "-" : `${submission.memory_kb} KB`
    );
    setText("submission-detail-created", formatDate(submission.created_at));
    setText("submission-detail-judged", submission.judged_at ? formatDate(submission.judged_at) : "-");
    setText("submission-detail-message", submission.verdict_message || "-");
    setText("submission-detail-code", submission.code);

    const status = document.getElementById("submission-detail-status");
    if (status) status.className = `status-pill status-${submission.status}`;
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
      loadSubmissionHistory(state.problem.id);
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
          if (state.problem) loadSubmissionHistory(state.problem.id);
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
