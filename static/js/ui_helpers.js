(function () {
  // Create toast container if missing
  function ensureToastContainer() {
    if (document.getElementById("globalToastContainer")) return;
    const container = document.createElement("div");
    container.id = "globalToastContainer";
    container.style.position = "fixed";
    container.style.zIndex = 1080;
    container.style.right = "1rem";
    container.style.top = "1rem";
    document.body.appendChild(container);
  }

  function createModalIfMissing(
    id,
    titleId,
    bodyId,
    inputId,
    confirmId,
    cancelId,
    options
  ) {
    if (document.getElementById(id)) return;
    const modal = document.createElement("div");
    modal.className = "modal fade";
    modal.id = id;
    modal.tabIndex = -1;
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="${titleId}"></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div id="${bodyId}" class="mb-2"></div>
            ${inputId ? `<input id="${inputId}" class="form-control" />` : ""}
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="${cancelId}">Отмена</button>
            <button type="button" class="btn btn-primary" id="${confirmId}">${
      options && options.confirmText ? options.confirmText : "OK"
    }</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  // ensure modals and container on DOMContentLoaded
  document.addEventListener("DOMContentLoaded", () => {
    ensureToastContainer();
    createModalIfMissing(
      "genericModal",
      "genericModalTitle",
      "genericModalBody",
      "genericModalInput",
      "genericModalConfirm",
      "genericModalCancel",
      { confirmText: "OK" }
    );
    createModalIfMissing(
      "confirmModal",
      "confirmModalTitle",
      "confirmModalBody",
      null,
      "confirmModalConfirm",
      "confirmModalCancel",
      { confirmText: "Подтвердить" }
    );
  });

  // showToast
  if (!window.showToast) {
    window.showToast = function (message, level = "info", delay = 3000) {
      ensureToastContainer();
      const cont = document.getElementById("globalToastContainer");
      const toastEl = document.createElement("div");
      toastEl.className =
        "toast align-items-center text-bg-" +
        (level === "error"
          ? "danger"
          : level === "success"
          ? "success"
          : "secondary") +
        " border-0";
      toastEl.setAttribute("role", "alert");
      toastEl.setAttribute("aria-live", "assertive");
      toastEl.setAttribute("aria-atomic", "true");
      toastEl.style.minWidth = "200px";
      toastEl.innerHTML = `
        <div class="d-flex">
          <div class="toast-body">${String(message)}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Закрыть"></button>
        </div>
      `;
      cont.appendChild(toastEl);
      try {
        const bsToast = new bootstrap.Toast(toastEl, { delay: delay });
        bsToast.show();
        toastEl.addEventListener("hidden.bs.toast", () => {
          toastEl.remove();
        });
      } catch (e) {
        // If bootstrap not ready, fallback to alert
        alert(message);
      }
    };
  }

  if (!window.showPromptModal) {
    window.showPromptModal = function (
      title,
      placeholder = "",
      defaultValue = ""
    ) {
      return new Promise((resolve) => {
        const modalEl = document.getElementById("genericModal");
        const modal = new bootstrap.Modal(modalEl);
        document.getElementById("genericModalTitle").textContent = title;
        document.getElementById("genericModalBody").textContent = placeholder;
        const input = document.getElementById("genericModalInput");
        input.value = defaultValue || "";
        input.focus();

        function onConfirm() {
          cleanup();
          resolve(input.value);
        }
        function onCancel() {
          cleanup();
          resolve(null);
        }
        function cleanup() {
          document
            .getElementById("genericModalConfirm")
            .removeEventListener("click", onConfirm);
          document
            .getElementById("genericModalCancel")
            .removeEventListener("click", onCancel);
          modal.hide();
        }
        document
          .getElementById("genericModalConfirm")
          .addEventListener("click", onConfirm);
        document
          .getElementById("genericModalCancel")
          .addEventListener("click", onCancel);
        modal.show();
      });
    };
  }

  if (!window.showSelectModal) {
    window.showSelectModal = function (
      title,
      options = [],
      selectedValue = null
    ) {
      return new Promise((resolve) => {
        // create modal if missing
        if (!document.getElementById("selectModal")) {
          const modal = document.createElement("div");
          modal.className = "modal fade";
          modal.id = "selectModal";
          modal.tabIndex = -1;
          modal.setAttribute("aria-hidden", "true");
          modal.innerHTML = `
            <div class="modal-dialog">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title" id="selectModalTitle"></h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                  <div id="selectModalBody" class="mb-2"></div>
                  <select id="selectModalSelect" class="form-select"></select>
                </div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="selectModalCancel">Отмена</button>
                  <button type="button" class="btn btn-primary" id="selectModalConfirm">OK</button>
                </div>
              </div>
            </div>
          `;
          document.body.appendChild(modal);
        }

        const modalEl = document.getElementById("selectModal");
        const modal = new bootstrap.Modal(modalEl);
        document.getElementById("selectModalTitle").textContent = title;
        const sel = document.getElementById("selectModalSelect");
        sel.innerHTML = "";
        options.forEach((opt) => {
          const o = document.createElement("option");
          o.value = opt.value;
          o.textContent = opt.text;
          sel.appendChild(o);
        });
        if (selectedValue !== null) sel.value = selectedValue;

        function onConfirm() {
          cleanup();
          resolve(sel.value);
        }
        function onCancel() {
          cleanup();
          resolve(null);
        }
        function cleanup() {
          document
            .getElementById("selectModalConfirm")
            .removeEventListener("click", onConfirm);
          document
            .getElementById("selectModalCancel")
            .removeEventListener("click", onCancel);
          modal.hide();
        }

        document
          .getElementById("selectModalConfirm")
          .addEventListener("click", onConfirm);
        document
          .getElementById("selectModalCancel")
          .addEventListener("click", onCancel);
        modal.show();
      });
    };
  }

  if (!window.showFormModal) {
    window.showFormModal = function (title, fields = []) {
      return new Promise((resolve) => {
        // create modal if missing
        if (!document.getElementById("formModal")) {
          const modal = document.createElement("div");
          modal.className = "modal fade";
          modal.id = "formModal";
          modal.tabIndex = -1;
          modal.setAttribute("aria-hidden", "true");
          modal.innerHTML = `
            <div class="modal-dialog">
              <div class="modal-content">
                <div class="modal-header">
                  <h5 class="modal-title" id="formModalTitle"></h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body" id="formModalBody"></div>
                <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="formModalCancel">Отмена</button>
                  <button type="button" class="btn btn-primary" id="formModalConfirm">Сохранить</button>
                </div>
              </div>
            </div>`;
          document.body.appendChild(modal);
        }

        const modalEl = document.getElementById("formModal");
        const modal = new bootstrap.Modal(modalEl);
        document.getElementById("formModalTitle").textContent = title;
        const body = document.getElementById("formModalBody");
        body.innerHTML = "";
        fields.forEach((f) => {
          const wrapper = document.createElement("div");
          wrapper.className = "mb-2";
          const label = document.createElement("label");
          const labelText = f.label || f.name;
          label.textContent = labelText + (f.required ? " *" : "");
          label.className = "form-label";
          wrapper.appendChild(label);
          let inp;
          if (f.type === "select") {
            inp = document.createElement("select");
            inp.className = "form-select";
            inp.id = "formModalField_" + f.name;
            (f.options || []).forEach((opt) => {
              const o = document.createElement("option");
              o.value = opt.value;
              o.textContent = opt.text;
              if (String(f.value || "") === String(opt.value))
                o.selected = true;
              inp.appendChild(o);
            });
          } else {
            inp = document.createElement("input");
            inp.className = "form-control";
            inp.type = f.type || "text";
            inp.id = "formModalField_" + f.name;
            inp.value = f.value || "";
          }
          if (f.required) inp.required = true;
          wrapper.appendChild(inp);
          body.appendChild(wrapper);
        });

        function onConfirm() {
          const out = {};
          fields.forEach((f) => {
            out[f.name] = document.getElementById(
              "formModalField_" + f.name
            ).value;
          });
          cleanup();
          resolve(out);
        }

        function onCancel() {
          cleanup();
          resolve(null);
        }

        function cleanup() {
          document
            .getElementById("formModalConfirm")
            .removeEventListener("click", onConfirm);
          document
            .getElementById("formModalCancel")
            .removeEventListener("click", onCancel);
          modal.hide();
        }

        document
          .getElementById("formModalConfirm")
          .addEventListener("click", onConfirm);
        document
          .getElementById("formModalCancel")
          .addEventListener("click", onCancel);
        modal.show();
      });
    };
  }

  if (!window.showConfirmModal) {
    window.showConfirmModal = function (message) {
      return new Promise((resolve) => {
        const modalEl = document.getElementById("confirmModal");
        const modal = new bootstrap.Modal(modalEl);
        // set body
        const body = document.getElementById("confirmModalBody");
        if (body) body.textContent = message;

        function onConfirm() {
          cleanup();
          resolve(true);
        }
        function onCancel() {
          cleanup();
          resolve(false);
        }
        function cleanup() {
          document
            .getElementById("confirmModalConfirm")
            .removeEventListener("click", onConfirm);
          document
            .getElementById("confirmModalCancel")
            .removeEventListener("click", onCancel);
          modal.hide();
        }
        document
          .getElementById("confirmModalConfirm")
          .addEventListener("click", onConfirm);
        document
          .getElementById("confirmModalCancel")
          .addEventListener("click", onCancel);
        modal.show();
      });
    };
  }
})();
