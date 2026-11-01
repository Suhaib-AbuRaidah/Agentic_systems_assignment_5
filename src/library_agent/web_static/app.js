(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const form = $("chat-form");
  const input = $("message-input");
  const sendButton = $("send-button");
  let catalog = [];
  let savedIds = new Set();
  let tokenTotal = 0;
  let busy = false;

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function setStatus(message) { $("request-status").textContent = message; }

  function addMessage(role, message, pending) {
    const empty = $("conversation").querySelector(".empty-conversation");
    if (empty) empty.remove();
    const box = node("div", "message message--" + role + (pending ? " message--pending" : ""));
    box.append(node("span", "message__label", role === "user" ? "You" : "Library agent"));
    box.append(node("div", "message__text", message));
    $("conversation").append(box);
    $("conversation").scrollTop = $("conversation").scrollHeight;
    return box;
  }

  function renderCatalog() {
    const filter = $("catalog-filter").value.trim().toLowerCase();
    const body = $("catalog-body");
    body.replaceChildren();
    let shown = 0;
    for (const book of catalog) {
      const haystack = [book.id, book.title, book.author, book.subject].join(" ").toLowerCase();
      if (!haystack.includes(filter)) continue;
      shown += 1;
      const row = node("tr");
      row.append(node("td", "catalog-id", book.id));
      row.append(node("td", "catalog-title", book.title));
      row.append(node("td", "", book.author));
      row.append(node("td", "", book.subject));
      const status = node("td");
      const badge = node("span", "ux-badge" + (savedIds.has(book.id) ? " ux-badge--good" : ""), savedIds.has(book.id) ? "Saved" : "Not saved");
      status.append(badge);
      row.append(status);
      body.append(row);
    }
    $("catalog-note").textContent = shown + " of " + catalog.length + " real published books shown. Demo collection; campus availability is not implied.";
  }

  function renderReadingList() {
    const books = catalog.filter((book) => savedIds.has(book.id));
    $("saved-count").textContent = String(books.length).padStart(2, "0");
    $("reading-count").textContent = books.length + (books.length === 1 ? " book" : " books");
    const list = $("reading-list");
    list.replaceChildren();
    if (!books.length) {
      list.append(node("p", "quiet", "No books saved yet. Ask the agent to save one."));
      return;
    }
    for (const book of books) {
      const item = node("div", "reading-item");
      item.append(node("span", "reading-item__id", book.id));
      const detail = node("div");
      detail.append(node("div", "reading-item__title", book.title));
      detail.append(node("div", "reading-item__author", book.author));
      item.append(detail);
      list.append(item);
    }
  }

  function toolSummary(call) {
    const result = call.result;
    if (result && typeof result === "object") {
      if (typeof result.count === "number") return result.count + (result.count === 1 ? " match returned" : " matches returned");
      if (result.book) return (result.already_saved ? "Already saved: " : "Saved: ") + result.book.title;
    }
    if (typeof result === "string") return result;
    return "Tool completed";
  }

  function renderActivity(calls) {
    if (!calls || !calls.length) return;
    const list = $("activity-list");
    const quiet = list.querySelector(".quiet");
    if (quiet) quiet.remove();
    for (const call of calls) {
      const item = node("div", "activity-entry");
      const top = node("div", "activity-entry__top");
      top.append(node("span", "tool-name", call.tool));
      const category = call.tool === "search_catalog" ? "DATA" : call.tool === "save_to_reading_list" ? "ACTION" : "ORCHESTRATION";
      top.append(node("span", "tool-type", category));
      item.append(top);
      const args = Object.entries(call.arguments || {}).map(([key, value]) => key + ": " + String(value)).join(" · ");
      item.append(node("div", "activity-entry__detail", args));
      item.append(node("div", "activity-entry__result" + (call.error ? " is-error" : ""), toolSummary(call)));
      list.prepend(item);
    }
  }

  async function fetchState() {
    const response = await fetch("/api/state", { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load the local library state.");
    const state = await response.json();
    catalog = state.catalog;
    savedIds = new Set(state.saved_ids);
    $("catalog-count").textContent = String(catalog.length).padStart(2, "0");
    $("model-name").textContent = state.model;
    if (!state.key_configured) {
      $("connection-badge").className = "ux-badge ux-badge--warn";
      $("connection-badge").innerHTML = '<span class="ux-badge__dot"></span>API key needed';
      setStatus("Set OPENAI_API_KEY in .env to send agent requests.");
      sendButton.disabled = true;
    }
    renderCatalog();
    renderReadingList();
  }

  async function sendMessage(message) {
    if (busy) return;
    const clean = message.trim();
    if (!clean) return;
    busy = true;
    sendButton.disabled = true;
    input.disabled = true;
    addMessage("user", clean);
    const pending = addMessage("assistant", "Thinking and checking the MCP tools…", true);
    input.value = "";
    setStatus("Agent is working…");
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: clean }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "The request could not be completed.");
      pending.classList.remove("message--pending");
      pending.querySelector(".message__text").textContent = result.answer || "The agent returned no message.";
      renderActivity(result.calls);
      tokenTotal += result.usage.total;
      $("usage-total").textContent = tokenTotal.toLocaleString() + " tokens used in this session";
      setStatus(result.usage.input + " input · " + result.usage.output + " output tokens for this request");
      await fetchState();
    } catch (error) {
      pending.classList.remove("message--pending");
      pending.querySelector(".message__text").textContent = error.message;
      setStatus("Request failed. You can try again.");
    } finally {
      busy = false;
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
      $("conversation").scrollTop = $("conversation").scrollHeight;
    }
  }

  form.addEventListener("submit", (event) => { event.preventDefault(); sendMessage(input.value); });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
  }));
  $("catalog-filter").addEventListener("input", renderCatalog);
  $("focus-toggle").addEventListener("click", () => {
    const focused = document.body.classList.toggle("focus-view");
    $("focus-toggle").setAttribute("aria-pressed", String(focused));
    $("focus-toggle").textContent = focused ? "Full view" : "Focus view";
  });
  if (new URLSearchParams(location.search).get("focus") === "1") $("focus-toggle").click();
  fetchState().catch((error) => {
    $("connection-badge").className = "ux-badge ux-badge--bad";
    $("connection-badge").textContent = "Connection error";
    setStatus(error.message);
    sendButton.disabled = true;
  });
})();
