// Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
// Dashboard: changing a row's state submits immediately. Asks for a note when
// "depended", and for the mandatory closing summary when "closed".
const closeDialog = document.getElementById("close-dialog");
function askClosingSummary(form, sel) {
  const resInput = form.querySelector('input[name="resolution"]');
  const text = document.getElementById("close-dialog-text");
  document.getElementById("close-dialog-title").textContent = resInput.dataset.title || "";
  text.value = resInput.value || "";
  closeDialog.returnValue = "";
  closeDialog.onclose = () => {
    if (closeDialog.returnValue === "ok" && text.value.trim()) {
      resInput.value = text.value.trim();
      form.submit();
    } else {
      sel.value = sel.dataset.current;  // cancelled: put the dropdown back
    }
  };
  closeDialog.showModal();
  text.focus();
}

document.querySelectorAll(".state-select").forEach((sel) => {
  sel.addEventListener("change", () => {
    const form = sel.form;
    if (sel.value === "closed" && closeDialog) {
      askClosingSummary(form, sel);
      return;
    }
    if (sel.value === "depended") {
      const depInput = form.querySelector('input[name="depends_on"]');
      const note = prompt("What / who is this task waiting on?", depInput.value || "");
      if (note === null) { sel.value = sel.dataset.current; return; }
      depInput.value = note;
    }
    form.submit();
  });
});

// Filter bars: dropdowns apply immediately, search applies after a short pause in typing.
document.querySelectorAll("form.auto-submit").forEach((form) => {
  form.querySelectorAll("select").forEach((s) => s.addEventListener("change", () => form.submit()));
  // date boxes: wait a moment so typing a year digit-by-digit doesn't reload each time
  form.querySelectorAll('input[type="date"]').forEach((d) => {
    let t;
    d.addEventListener("change", () => {
      clearTimeout(t);
      t = setTimeout(() => { if (d.value && d.value.slice(0, 4) >= "1990") form.submit(); }, 900);
    });
  });
  const search = form.querySelector('input[type="search"]');
  if (search) {
    let timer;
    search.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => form.submit(), 500);
    });
    // keep the cursor in the search box (at the end) after the page reloads
    if (search.value) {
      search.focus();
      search.setSelectionRange(search.value.length, search.value.length);
    }
  }
});

// Review: "Include" checkboxes reload the review with an updated exclude list,
// so the summary numbers and every download match what is shown.
document.querySelectorAll(".rv-toggle").forEach((box) => {
  box.addEventListener("change", () => {
    const url = new URL(window.location.href);
    const ids = new Set((url.searchParams.get("exclude") || "").split(",").filter(Boolean));
    if (box.checked) ids.delete(box.dataset.id); else ids.add(box.dataset.id);
    if (ids.size) url.searchParams.set("exclude", [...ids].sort((a, b) => a - b).join(","));
    else url.searchParams.delete("exclude");
    try { sessionStorage.setItem("mytodo-scroll", String(window.scrollY)); } catch (e) {}
    window.location.href = url.toString();
  });
});
try {
  const y = sessionStorage.getItem("mytodo-scroll");
  if (y !== null) { sessionStorage.removeItem("mytodo-scroll"); window.scrollTo(0, Number(y)); }
} catch (e) {}

// Review: confirm before saving a review.
const saveBtn = document.getElementById("save-review");
if (saveBtn) {
  saveBtn.addEventListener("click", (ev) => {
    const msg = `Save the review for ${saveBtn.dataset.period}?\n\n` +
      "A copy is kept under Past reviews and your next review will start the day after this period.";
    if (!confirm(msg)) { ev.preventDefault(); return; }
    saveBtn.form.querySelector('input[name="confirm"]').value = "yes";
  });
}
document.querySelectorAll("form.confirm-form").forEach((f) => {
  f.addEventListener("submit", (ev) => { if (!confirm(f.dataset.confirm)) ev.preventDefault(); });
});

// Task form / detail: show "Depends on" only for depended, and the (required)
// closing summary only for closed.
const stateField = document.getElementById("state-field");
const dependsField = document.getElementById("depends-field");
const resolutionField = document.getElementById("resolution-field");
if (stateField) {
  const sync = () => {
    if (dependsField) dependsField.hidden = stateField.value !== "depended";
    if (resolutionField) {
      const closing = stateField.value === "closed";
      resolutionField.hidden = !closing;
      const ta = resolutionField.querySelector("textarea");
      ta.required = closing;
      if (closing && document.activeElement === stateField) ta.focus();
    }
  };
  stateField.addEventListener("change", sync);
  sync();
}

// Backup page: confirmation checkbox only matters for "replace".
const replace = document.getElementById("mode-replace");
const confirmRow = document.getElementById("confirm-row");
if (replace && confirmRow) {
  const sync = () => { confirmRow.hidden = !replace.checked; };
  document.querySelectorAll('input[name="mode"]').forEach((r) => r.addEventListener("change", sync));
  sync();
}
