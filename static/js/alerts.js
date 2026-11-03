// Notification Drawer and Real-Time Alerts Controller

function toggleNotificationDrawer() {
    const drawer = document.getElementById("notificationDrawer");
    const overlay = document.getElementById("drawerOverlay");
    if (!drawer) return;

    if (drawer.classList.contains("translate-x-full")) {
        drawer.classList.remove("translate-x-full");
        if (overlay) overlay.classList.remove("hidden");
        loadNotificationAlerts();
    } else {
        drawer.classList.add("translate-x-full");
        if (overlay) overlay.classList.add("hidden");
    }
}

async function loadNotificationAlerts() {
    const container = document.getElementById("alertsContainer");
    const countBadge = document.getElementById("alertsCountBadge");
    if (!container) return;

    container.innerHTML = `
        <div class="flex items-center justify-center py-12 text-slate-400">
            <svg class="animate-spin h-6 w-6 mr-2 text-emerald-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            Loading alerts...
        </div>
    `;

    try {
        const response = await fetch("/api/alerts");
        const data = await response.json();

        if (data.success && data.alerts) {
            if (countBadge) {
                countBadge.innerText = data.count;
                if (data.count === 0) {
                    countBadge.classList.add("hidden");
                } else {
                    countBadge.classList.remove("hidden");
                }
            }

            if (data.alerts.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-12 text-slate-400">
                        <svg class="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p class="font-medium text-slate-600">All systems optimal!</p>
                        <p class="text-xs text-slate-400 mt-1">No pending alerts, expired stocks, or overdue dues.</p>
                    </div>
                `;
                return;
            }

            let html = '<div class="space-y-3">';
            data.alerts.forEach(alert => {
                let badgeColor = "bg-slate-100 text-slate-800 border-slate-200";
                if (alert.severity === "danger") badgeColor = "bg-rose-50 text-rose-700 border-rose-200";
                else if (alert.severity === "warning") badgeColor = "bg-amber-50 text-amber-700 border-amber-200";
                else if (alert.severity === "success") badgeColor = "bg-emerald-50 text-emerald-700 border-emerald-200";
                else if (alert.severity === "info") badgeColor = "bg-blue-50 text-blue-700 border-blue-200";

                html += `
                    <div class="p-3.5 rounded-xl border ${badgeColor} transition hover:shadow-sm">
                        <div class="flex items-start justify-between gap-2">
                            <h4 class="text-sm font-semibold">${alert.title}</h4>
                            <span class="text-[10px] text-slate-400 whitespace-nowrap">${alert.time}</span>
                        </div>
                        <p class="text-xs mt-1 leading-relaxed opacity-90">${alert.message}</p>
                        ${alert.link ? `
                            <a href="${alert.link}" class="inline-flex items-center text-xs font-semibold mt-2.5 hover:underline">
                                Take Action &rarr;
                            </a>
                        ` : ''}
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }
    } catch (e) {
        console.error("Alert load error:", e);
        container.innerHTML = `<p class="text-sm text-rose-500 py-6 text-center">Failed to load alerts.</p>`;
    }
}
