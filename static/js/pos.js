// POS Terminal Client-Side Logic

let cart = [];
let searchDebounceTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("posSearchInput");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            clearTimeout(searchDebounceTimer);
            const query = e.target.value.trim();
            if (query.length < 1) {
                hideSearchResults();
                return;
            }
            searchDebounceTimer = setTimeout(() => {
                fetchMedicines(query);
            }, 250);
        });

        // Close search results on click outside
        document.addEventListener("click", (e) => {
            if (!e.target.closest("#posSearchContainer")) {
                hideSearchResults();
            }
        });
    }

    // Discount and Tax inputs
    const discountInput = document.getElementById("discountPercentInput");
    const taxInput = document.getElementById("taxPercentInput");
    const paidInput = document.getElementById("paidAmountInput");

    if (discountInput) discountInput.addEventListener("input", updateTotals);
    if (taxInput) taxInput.addEventListener("input", updateTotals);
    if (paidInput) paidInput.addEventListener("input", updateDuePreview);

    renderCart();
});

async function fetchMedicines(query) {
    const resultsContainer = document.getElementById("posSearchResults");
    if (!resultsContainer) return;

    try {
        const res = await fetch(`/api/medicines/search?q=${encodeURIComponent(query)}&active_only=1`);
        const data = await res.json();

        if (data.success && data.medicines) {
            if (data.medicines.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="p-4 text-center text-sm text-slate-400">
                        No medicines found matching "${query}"
                    </div>
                `;
            } else {
                let html = '<div class="divide-y divide-slate-100 max-h-72 overflow-y-auto">';
                data.medicines.forEach(m => {
                    const isExpired = m.is_expired;
                    const isOutOfStock = m.quantity <= 0;

                    let statusBadge = `<span class="px-2 py-0.5 text-xs font-semibold rounded-md bg-emerald-50 text-emerald-700">Stock: ${m.quantity}</span>`;
                    if (isExpired) {
                        statusBadge = `<span class="px-2 py-0.5 text-xs font-semibold rounded-md bg-rose-100 text-rose-800">EXPIRED (${m.expiry_date})</span>`;
                    } else if (isOutOfStock) {
                        statusBadge = `<span class="px-2 py-0.5 text-xs font-semibold rounded-md bg-slate-100 text-slate-600">Out of Stock</span>`;
                    } else if (m.is_expiring_soon) {
                        statusBadge = `<span class="px-2 py-0.5 text-xs font-semibold rounded-md bg-amber-50 text-amber-700">Expires soon (${m.expiry_date})</span>`;
                    }

                    html += `
                        <div class="p-3 hover:bg-slate-50 flex items-center justify-between cursor-pointer transition ${isExpired ? 'bg-rose-50/50' : ''}"
                             onclick='handleSelectMedicine(${JSON.stringify(m).replace(/'/g, "&#39;")})'>
                            <div>
                                <div class="font-semibold text-slate-800 text-sm flex items-center gap-2">
                                    ${m.name}
                                    ${m.generic_name ? `<span class="text-xs text-slate-400 font-normal">(${m.generic_name})</span>` : ''}
                                </div>
                                <div class="text-xs text-slate-500 mt-0.5">
                                    Batch: <span class="font-mono">${m.batch_number}</span> | Cat: ${m.category} | Rack: ${m.rack_location || 'General'}
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="font-bold text-slate-900 text-sm">₹${m.unit_price.toFixed(2)}</div>
                                <div class="mt-1">${statusBadge}</div>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                resultsContainer.innerHTML = html;
            }
            resultsContainer.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Search error:", e);
    }
}

function hideSearchResults() {
    const resultsContainer = document.getElementById("posSearchResults");
    if (resultsContainer) resultsContainer.classList.add("hidden");
}

function handleSelectMedicine(med) {
    hideSearchResults();

    // Check expiry
    if (med.is_expired) {
        showPosAlert(`Cannot add "${med.name}": Medicine expired on ${med.expiry_date}! Expired items are strictly blocked from billing.`, "danger");
        return;
    }

    // Check stock
    if (med.quantity <= 0) {
        showPosAlert(`Cannot add "${med.name}": Out of stock! You can place a reservation for the customer instead.`, "warning");
        return;
    }

    // Check if item already exists in cart
    const existingIndex = cart.findIndex(item => item.id === med.id);
    if (existingIndex > -1) {
        if (cart[existingIndex].quantity >= med.quantity) {
            showPosAlert(`Cannot add more "${med.name}": Only ${med.quantity} units available in stock.`, "warning");
            return;
        }
        cart[existingIndex].quantity += 1;
    } else {
        cart.push({
            id: med.id,
            name: med.name,
            batch_number: med.batch_number,
            unit_price: parseFloat(med.unit_price),
            max_stock: parseInt(med.quantity),
            quantity: 1
        });
    }

    // Clear search input
    const searchInput = document.getElementById("posSearchInput");
    if (searchInput) {
        searchInput.value = "";
        searchInput.focus();
    }

    renderCart();
}

function renderCart() {
    const cartContainer = document.getElementById("cartItemsBody");
    const emptyState = document.getElementById("cartEmptyState");
    const checkoutBtn = document.getElementById("posCheckoutBtn");
    if (!cartContainer) return;

    if (cart.length === 0) {
        cartContainer.innerHTML = "";
        if (emptyState) emptyState.classList.remove("hidden");
        if (checkoutBtn) checkoutBtn.disabled = true;
        updateTotals();
        return;
    }

    if (emptyState) emptyState.classList.add("hidden");
    if (checkoutBtn) checkoutBtn.disabled = false;

    let html = "";
    cart.forEach((item, index) => {
        const lineTotal = (item.quantity * item.unit_price).toFixed(2);
        html += `
            <tr class="border-b border-slate-100 hover:bg-slate-50/70 transition">
                <td class="py-3 px-3">
                    <div class="font-medium text-slate-800 text-sm">${item.name}</div>
                    <div class="text-[11px] text-slate-400 font-mono">Batch: ${item.batch_number} (Avail: ${item.max_stock})</div>
                </td>
                <td class="py-3 px-3 text-right font-medium text-slate-700 text-sm">
                    ₹${item.unit_price.toFixed(2)}
                </td>
                <td class="py-3 px-3">
                    <div class="flex items-center justify-center gap-1">
                        <button type="button" onclick="adjustQty(${index}, -1)" class="w-6 h-6 rounded bg-slate-100 text-slate-600 hover:bg-slate-200 flex items-center justify-center font-bold text-xs">-</button>
                        <input type="number" min="1" max="${item.max_stock}" value="${item.quantity}" 
                               onchange="setQty(${index}, this.value)"
                               class="w-12 text-center text-xs font-semibold py-1 border border-slate-200 rounded focus:ring-1 focus:ring-emerald-500">
                        <button type="button" onclick="adjustQty(${index}, 1)" class="w-6 h-6 rounded bg-slate-100 text-slate-600 hover:bg-slate-200 flex items-center justify-center font-bold text-xs">+</button>
                    </div>
                </td>
                <td class="py-3 px-3 text-right font-bold text-slate-900 text-sm">
                    ₹${lineTotal}
                </td>
                <td class="py-3 px-2 text-center">
                    <button type="button" onclick="removeCartItem(${index})" class="text-rose-500 hover:text-rose-700 p-1 rounded hover:bg-rose-50 transition">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </td>
            </tr>
        `;
    });

    cartContainer.innerHTML = html;
    updateTotals();
}

function adjustQty(index, delta) {
    const item = cart[index];
    const newQty = item.quantity + delta;
    if (newQty <= 0) {
        removeCartItem(index);
        return;
    }
    if (newQty > item.max_stock) {
        showPosAlert(`Cannot add more than available stock (${item.max_stock} units) for "${item.name}".`, "warning");
        return;
    }
    item.quantity = newQty;
    renderCart();
}

function setQty(index, value) {
    const val = parseInt(value) || 1;
    const item = cart[index];
    if (val <= 0) {
        removeCartItem(index);
        return;
    }
    if (val > item.max_stock) {
        showPosAlert(`Max available units for "${item.name}" is ${item.max_stock}. Adjusted to maximum.`, "warning");
        item.quantity = item.max_stock;
    } else {
        item.quantity = val;
    }
    renderCart();
}

function removeCartItem(index) {
    cart.splice(index, 1);
    renderCart();
}

function clearCart() {
    if (cart.length > 0 && confirm("Are you sure you want to clear the entire cart?")) {
        cart = [];
        renderCart();
    }
}

function updateTotals() {
    let subtotal = 0;
    cart.forEach(item => {
        subtotal += item.quantity * item.unit_price;
    });

    const discountPercent = parseFloat(document.getElementById("discountPercentInput")?.value || 0);
    const taxPercent = parseFloat(document.getElementById("taxPercentInput")?.value || 5.0);

    const discountAmount = subtotal * (discountPercent / 100.0);
    const taxableAmount = Math.max(0, subtotal - discountAmount);
    const taxAmount = taxableAmount * (taxPercent / 100.0);
    const grandTotal = taxableAmount + taxAmount;

    // Update DOM displays
    const subtotalEl = document.getElementById("posSubtotalDisplay");
    const discountEl = document.getElementById("posDiscountDisplay");
    const taxEl = document.getElementById("posTaxDisplay");
    const totalEl = document.getElementById("posTotalDisplay");

    if (subtotalEl) subtotalEl.innerText = `₹${subtotal.toFixed(2)}`;
    if (discountEl) discountEl.innerText = `-₹${discountAmount.toFixed(2)}`;
    if (taxEl) taxEl.innerText = `+₹${taxAmount.toFixed(2)}`;
    if (totalEl) totalEl.innerText = `₹${grandTotal.toFixed(2)}`;

    // Update default paid amount if not touched
    const paidInput = document.getElementById("paidAmountInput");
    const isCredit = document.getElementById("posPaymentMethod")?.value === "credit";
    if (paidInput && !isCredit && (paidInput.value === "" || parseFloat(paidInput.value) === 0 || !paidInput.dataset.manual)) {
        paidInput.value = grandTotal.toFixed(2);
    }
    updateDuePreview();
}

function updateDuePreview() {
    const totalText = document.getElementById("posTotalDisplay")?.innerText.replace("₹", "") || "0";
    const grandTotal = parseFloat(totalText);
    const paidAmount = parseFloat(document.getElementById("paidAmountInput")?.value || 0);
    const dueAmount = Math.max(0, grandTotal - paidAmount);

    const duePreviewEl = document.getElementById("posDueAmountDisplay");
    const dueContainer = document.getElementById("posDueContainer");

    if (duePreviewEl) duePreviewEl.innerText = `₹${dueAmount.toFixed(2)}`;
    if (dueContainer) {
        if (dueAmount > 0) {
            dueContainer.classList.remove("hidden");
        } else {
            dueContainer.classList.add("hidden");
        }
    }
}

function showPosAlert(message, type = "info") {
    const alertBox = document.getElementById("posAlertBanner");
    if (!alertBox) return;

    let bgClass = "bg-blue-50 text-blue-800 border-blue-200";
    if (type === "danger") bgClass = "bg-rose-50 text-rose-800 border-rose-200";
    if (type === "warning") bgClass = "bg-amber-50 text-amber-800 border-amber-200";
    if (type === "success") bgClass = "bg-emerald-50 text-emerald-800 border-emerald-200";

    alertBox.className = `p-3 rounded-xl border text-sm font-medium flex items-center justify-between shadow-sm ${bgClass}`;
    alertBox.innerHTML = `
        <div class="flex items-center gap-2">
            <span>${message}</span>
        </div>
        <button onclick="this.parentElement.classList.add('hidden')" class="text-xs font-bold px-2 py-0.5 rounded hover:bg-black/10">&times;</button>
    `;
    alertBox.classList.remove("hidden");
    setTimeout(() => {
        alertBox.classList.add("hidden");
    }, 6000);
}

// Payment method change handler
function handlePaymentMethodChange() {
    const method = document.getElementById("posPaymentMethod").value;
    const paidInput = document.getElementById("paidAmountInput");
    const gatewayBtn = document.getElementById("triggerGatewayModalBtn");

    if (method === "credit") {
        if (paidInput) {
            paidInput.value = "0.00";
            paidInput.dataset.manual = "true";
        }
        if (gatewayBtn) gatewayBtn.classList.add("hidden");
    } else if (method === "mock_gateway") {
        if (gatewayBtn) gatewayBtn.classList.remove("hidden");
    } else {
        if (gatewayBtn) gatewayBtn.classList.add("hidden");
        const totalText = document.getElementById("posTotalDisplay")?.innerText.replace("₹", "") || "0";
        if (paidInput) {
            paidInput.value = parseFloat(totalText).toFixed(2);
            delete paidInput.dataset.manual;
        }
    }
    updateDuePreview();
}

// Open Mock Payment Gateway Modal
function openGatewayModal() {
    const totalText = document.getElementById("posTotalDisplay")?.innerText.replace("₹", "") || "0";
    const amount = parseFloat(totalText);
    if (amount <= 0) {
        showPosAlert("Cart is empty or total is zero.", "warning");
        return;
    }
    document.getElementById("modalGatewayAmount").innerText = `₹${amount.toFixed(2)}`;
    document.getElementById("mockGatewayModal").classList.remove("hidden");
}

function closeGatewayModal() {
    document.getElementById("mockGatewayModal").classList.add("hidden");
}

async function simulateGatewayCheckout(simulateFailure = false) {
    const totalText = document.getElementById("posTotalDisplay")?.innerText.replace("₹", "") || "0";
    const amount = parseFloat(totalText);
    const mode = document.getElementById("gatewayPayMode")?.value || "card";
    const statusMsg = document.getElementById("gatewayModalStatus");

    if (statusMsg) {
        statusMsg.innerHTML = `<span class="text-blue-600 animate-pulse font-medium">Connecting to Payment Gateway...</span>`;
    }

    try {
        const res = await fetch("/api/payments/mock-gateway", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                amount: amount,
                mode: mode,
                simulate_failure: simulateFailure
            })
        });
        const data = await res.json();

        if (data.success) {
            if (statusMsg) {
                statusMsg.innerHTML = `<span class="text-emerald-600 font-bold">Authorized! Ref: ${data.transaction_ref}</span>`;
            }
            setTimeout(() => {
                closeGatewayModal();
                showPosAlert(`Payment authorized via Mock Gateway! Reference: ${data.transaction_ref}`, "success");
                // Auto submit bill
                submitCheckout(data.transaction_ref);
            }, 1000);
        } else {
            if (statusMsg) {
                statusMsg.innerHTML = `<span class="text-rose-600 font-semibold">${data.message || 'Payment Declined'}</span>`;
            }
        }
    } catch (e) {
        if (statusMsg) statusMsg.innerHTML = `<span class="text-rose-600">Gateway error: ${e.message}</span>`;
    }
}

// Main Checkout Submission
async function submitCheckout(customTxnRef = null) {
    if (cart.length === 0) {
        showPosAlert("Cannot process sale: Cart is empty.", "warning");
        return;
    }

    const customerName = document.getElementById("customerNameInput")?.value.trim() || "Walk-in Customer";
    const customerPhone = document.getElementById("customerPhoneInput")?.value.trim() || "";
    const discountPercent = parseFloat(document.getElementById("discountPercentInput")?.value || 0);
    const taxPercent = parseFloat(document.getElementById("taxPercentInput")?.value || 5.0);
    const paymentMethod = document.getElementById("posPaymentMethod")?.value || "cash";
    const paidAmount = parseFloat(document.getElementById("paidAmountInput")?.value || 0);
    const notes = document.getElementById("posNotesInput")?.value.trim() || "";

    const payload = {
        customer_name: customerName,
        customer_phone: customerPhone,
        items: cart.map(i => ({ medicine_id: i.id, quantity: i.quantity, unit_price: i.unit_price })),
        discount_percent: discountPercent,
        tax_percent: taxPercent,
        payment_method: paymentMethod,
        paid_amount: paidAmount,
        notes: notes + (customTxnRef ? ` [Gateway Ref: ${customTxnRef}]` : "")
    };

    const submitBtn = document.getElementById("posCheckoutBtn");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            Processing Sale...
        `;
    }

    try {
        const response = await fetch("/api/bills/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (result.success) {
            cart = [];
            // Redirect to the generated invoice for instant printing
            window.location.href = `/bills/${result.bill_id}`;
        } else {
            showPosAlert(`Billing failed: ${result.error}`, "danger");
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `Complete Sale & Print Invoice`;
            }
        }
    } catch (e) {
        showPosAlert(`Network error: ${e.message}`, "danger");
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `Complete Sale & Print Invoice`;
        }
    }
}
