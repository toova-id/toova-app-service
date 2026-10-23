/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { onWillStart, Component, useState } from "@odoo/owl";

let appOpenSequence = 0;

export class HomeDashboard extends Component {
    setup() {
        this.menuService = useService("menu");
        this.user = useService("user");
        this.orm = useService("orm");
        this.state = useState({
            metrics: [],
            recentSales: [],
            salesTrend: [],
            pipelineStages: [],
            activities: [],
            activitySummary: [],
            activityChartStyle: "",
            analyticsReady: false,
            refreshing: false,
            openingApp: false,
            lastUpdated: "Updating…",
        });
        onWillStart(() => this.loadAnalytics());
    }

    get apps() {
        return this.menuService.getApps();
    }

    get activityTotal() {
        return this.state.activitySummary.reduce((total, item) => total + item.value, 0);
    }

    getAppIcon(app) {
        if (!app.webIconData) {
            return null;
        }
        if (app.webIconData.startsWith("data:image") || app.webIconData.startsWith("/")) {
            return app.webIconData;
        }
        const prefix = app.webIconData.startsWith("P")
            ? "data:image/svg+xml;base64,"
            : "data:image/png;base64,";
        return prefix + app.webIconData.replace(/\s/g, "");
    }

    getAppInitial(app) {
        return app.name.trim().charAt(0).toLocaleUpperCase();
    }

    formatMoney(value) {
        return new Intl.NumberFormat(undefined, {
            notation: "compact",
            maximumFractionDigits: 1,
        }).format(value || 0);
    }

    formatDate(value) {
        if (!value) {
            return "No deadline";
        }
        return new Intl.DateTimeFormat(undefined, {
            month: "short",
            day: "numeric",
        }).format(new Date(`${value}T00:00:00`));
    }

    getToday() {
        const today = new Date();
        const month = String(today.getMonth() + 1).padStart(2, "0");
        const day = String(today.getDate()).padStart(2, "0");
        return `${today.getFullYear()}-${month}-${day}`;
    }

    async refreshAnalytics() {
        if (this.state.refreshing) {
            return;
        }
        this.state.refreshing = true;
        try {
            await this.loadAnalytics();
        } finally {
            this.state.refreshing = false;
        }
    }

    async loadAnalytics() {
        const today = this.getToday();
        const activityDomain = [["user_id", "=", this.user.userId]];
        const [customers, overdue, dueToday, upcoming, activities] = await Promise.all([
            this.orm
                .searchCount("res.partner", [["is_company", "=", true], ["active", "=", true]])
                .catch(() => 0),
            this.orm
                .searchCount("mail.activity", [...activityDomain, ["date_deadline", "<", today]])
                .catch(() => 0),
            this.orm
                .searchCount("mail.activity", [...activityDomain, ["date_deadline", "=", today]])
                .catch(() => 0),
            this.orm
                .searchCount("mail.activity", [...activityDomain, ["date_deadline", ">", today]])
                .catch(() => 0),
            this.orm
                .searchRead(
                    "mail.activity",
                    activityDomain,
                    ["summary", "res_name", "activity_type_id", "date_deadline", "res_model"],
                    { limit: 6, order: "date_deadline asc, id desc" }
                )
                .catch(() => []),
        ]);

        const metrics = [
            { id: "customers", label: "Customers", value: customers, detail: "Active companies", icon: "fa-building-o" },
        ];
        let recentSales = [];
        let salesTrend = [];
        let pipelineStages = [];

        const hasSales = await this.user
            .hasGroup("sales_team.group_sale_salesman")
            .catch(() => false);
        if (hasSales) {
            const [pipeline, quotations, sales, orders, trend, stages] = await Promise.all([
                this.orm
                    .searchCount("crm.lead", [["type", "=", "opportunity"], ["active", "=", true]])
                    .catch(() => 0),
                this.orm
                    .searchCount("sale.order", [["state", "in", ["draft", "sent"]]])
                    .catch(() => 0),
                this.orm
                    .readGroup("sale.order", [["state", "in", ["sale", "done"]]], ["amount_total:sum"], [])
                    .catch(() => []),
                this.orm
                    .searchRead(
                        "sale.order",
                        [["state", "in", ["sale", "done"]]],
                        ["name", "partner_id", "amount_total", "date_order"],
                        { limit: 6, order: "date_order desc" }
                    )
                    .catch(() => []),
                this.orm
                    .readGroup(
                        "sale.order",
                        [["state", "in", ["sale", "done"]]],
                        ["amount_total:sum"],
                        ["date_order:month"],
                        { lazy: false, orderby: "date_order:month desc", limit: 6 }
                    )
                    .catch(() => []),
                this.orm
                    .readGroup(
                        "crm.lead",
                        [["type", "=", "opportunity"], ["active", "=", true]],
                        ["expected_revenue:sum"],
                        ["stage_id"],
                        { lazy: false, limit: 6 }
                    )
                    .catch(() => []),
            ]);
            metrics.unshift(
                { id: "pipeline", label: "Pipeline", value: pipeline, detail: "Open opportunities", icon: "fa-line-chart" },
                { id: "quotations", label: "Quotations", value: quotations, detail: "Awaiting confirmation", icon: "fa-file-text-o" },
                {
                    id: "revenue",
                    label: "Sales revenue",
                    value: this.formatMoney(sales[0] && sales[0].amount_total),
                    detail: "Confirmed orders",
                    icon: "fa-long-arrow-up",
                }
            );
            recentSales = orders;
            const points = trend
                .slice()
                .reverse()
                .map((point) => ({
                    label: point["date_order:month"] || "—",
                    value: point.amount_total || 0,
                }));
            const max = Math.max(...points.map((point) => point.value), 1);
            salesTrend = points.map((point) => ({
                ...point,
                height: Math.max(6, Math.round((point.value / max) * 100)),
            }));
            const maxPipeline = Math.max(...stages.map((stage) => stage.expected_revenue || 0), 1);
            pipelineStages = stages.map((stage) => ({
                id: stage.stage_id ? stage.stage_id[0] : "none",
                label: stage.stage_id ? stage.stage_id[1] : "Unassigned",
                count: stage.stage_id_count || 0,
                value: stage.expected_revenue || 0,
                width: Math.max(4, Math.round(((stage.expected_revenue || 0) / maxPipeline) * 100)),
            }));
        }

        metrics.push({
            id: "activities",
            label: "Activities",
            value: overdue + dueToday + upcoming,
            detail: `${overdue} overdue`,
            icon: "fa-check-square-o",
        });
        const activityCount = overdue + dueToday + upcoming;
        const totalActivities = Math.max(activityCount, 1);
        const overdueEnd = Math.round((overdue / totalActivities) * 100);
        const todayEnd = overdueEnd + Math.round((dueToday / totalActivities) * 100);

        this.state.metrics = metrics;
        this.state.recentSales = recentSales;
        this.state.salesTrend = salesTrend;
        this.state.pipelineStages = pipelineStages;
        this.state.activities = activities;
        this.state.activitySummary = [
            { id: "overdue", label: "Overdue", value: overdue },
            { id: "today", label: "Due today", value: dueToday },
            { id: "upcoming", label: "Upcoming", value: upcoming },
        ];
        this.state.activityChartStyle = activityCount
            ? `background: conic-gradient(var(--destructive) 0 ${overdueEnd}%, #d99b25 ${overdueEnd}% ${todayEnd}%, var(--primary) ${todayEnd}% 100%)`
            : "background: var(--muted)";
        this.state.lastUpdated = new Intl.DateTimeFormat(undefined, {
            hour: "2-digit",
            minute: "2-digit",
        }).format(new Date());
        this.state.analyticsReady = true;
    }

    async selectApp(app) {
        if (this.state.openingApp) {
            return;
        }
        this.state.openingApp = true;
        const loadingId = `workspace-app-${app.id}-${++appOpenSequence}`;
        this.env.bus.trigger("WORKSPACE:APP-OPENING");
        this.env.bus.trigger("RPC:REQUEST", loadingId);
        try {
            await this.menuService.selectMenu(app);
            this.env.bus.trigger("WORKSPACE:APP-OPENED");
        } catch (error) {
            this.env.bus.trigger("WORKSPACE:APP-FAILED");
            throw error;
        } finally {
            this.state.openingApp = false;
            this.env.bus.trigger("RPC:RESPONSE", loadingId);
        }
    }
}

HomeDashboard.template = "web.HomeDashboard";
