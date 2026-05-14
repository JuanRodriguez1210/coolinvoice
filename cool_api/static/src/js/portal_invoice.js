/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalInvoiceForm = publicWidget.Widget.extend({

    selector: '.inv-wrapper',

    start: function () {

        const body = document.getElementById('linesBody');

        if (!body) {
            return this._super(...arguments);
        }

        const btn = document.getElementById('btnAddLine');

        const subtotalEl = document.getElementById('displaySubtotal');
        const totalEl = document.getElementById('displayTotal');

        const productsEl = document.getElementById('inv-products-data');
        const accountsEl = document.getElementById('inv-accounts-data');

        const products = JSON.parse(
            productsEl?.textContent || '[]'
        );

        const accounts = JSON.parse(
            accountsEl?.textContent || '[]'
        );

        let lineCount = 0;

        function recalculateTotals() {

            let total = 0;

            body.querySelectorAll('tr').forEach(function (row) {

                const qty = parseFloat(
                    row.querySelector('.line-qty')?.value || 0
                );

                const price = parseFloat(
                    row.querySelector('.line-price')?.value || 0
                );

                const lineTotal = qty * price;

                row.querySelector('.line-total').textContent =
                    lineTotal.toFixed(2);

                total += lineTotal;
            });

            subtotalEl.textContent = total.toFixed(2);
            totalEl.textContent = total.toFixed(2);
        }

        function buildProductOptions() {

            let html = '<option value="">— Producto —</option>';

            products.forEach(function (p) {

                html += `
                    <option value="${p.id}"
                            data-price="${p.price}"
                            data-account="${p.acct}">
                        ${p.name}
                    </option>
                `;
            });

            return html;
        }

        function buildAccountOptions() {

            let html = '<option value="">— Cuenta —</option>';

            accounts.forEach(function (a) {

                html += `
                    <option value="${a.id}">
                        ${a.name}
                    </option>
                `;
            });

            return html;
        }

        function addLine() {

            const idx = lineCount++;

            const tr = document.createElement('tr');

            tr.innerHTML = `
                <td>
                    <select name="line_product_${idx}"
                            class="inv-select line-product">
                        ${buildProductOptions()}
                    </select>
                </td>

                <td>
                    <input type="text"
                           name="line_name_${idx}"
                           class="inv-input"
                           placeholder="Descripción">
                </td>

                <td>
                    <select name="line_account_${idx}"
                            class="inv-select line-account">
                        ${buildAccountOptions()}
                    </select>
                </td>

                <td>
                    <input type="number"
                           step="0.01"
                           min="1"
                           value="1"
                           name="line_qty_${idx}"
                           class="inv-input line-qty">
                </td>

                <td>
                    <input type="number"
                           step="0.01"
                           min="0"
                           value="0"
                           name="line_price_${idx}"
                           class="inv-input line-price">
                </td>

                <td>
                    <span class="line-total">0.00</span>
                </td>
            `;

            body.appendChild(tr);

            const productSelect = tr.querySelector('.line-product');
            const accountSelect = tr.querySelector('.line-account');
            const qtyInput = tr.querySelector('.line-qty');
            const priceInput = tr.querySelector('.line-price');

            productSelect.addEventListener('change', function () {

                const option = this.options[this.selectedIndex];

                priceInput.value = option.dataset.price || 0;

                if (option.dataset.account) {
                    accountSelect.value = option.dataset.account;
                }

                recalculateTotals();
            });

            qtyInput.addEventListener(
                'input',
                recalculateTotals
            );

            priceInput.addEventListener(
                'input',
                recalculateTotals
            );

            recalculateTotals();
        }

        if (btn) {

            btn.addEventListener('click', function () {
                addLine();
            });
        }

        addLine();

        return this._super(...arguments);
    },
});