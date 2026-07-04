/* simulation.js — HabitFlow team model */

const AGENTS = {
  coordinator:       { id: "coordinator",       name: "Coordenador",  role: "Orquestrador",     color: "var(--coordinator)", icon: "🎯" },
  "collector-agent": { id: "collector-agent", name: "Collector",    role: "Check-in",         color: "var(--collector)",   icon: "📝" },
  "analyzer-agent":  { id: "analyzer-agent",  name: "Analyzer",     role: "Métricas / NLP",   color: "var(--analyzer)",    icon: "🔍" },
  "coach-agent":     { id: "coach-agent",     name: "Coach",        role: "Recomendações",   color: "var(--coach)",       icon: "🧠" },
  "guardian-agent":  { id: "guardian-agent",  name: "Guardian",     role: "Saúde / LGPD",   color: "var(--guardian)",    icon: "🛡️" },
  "notifier-agent":  { id: "notifier-agent",  name: "Notifier",     role: "Feedback",       color: "var(--notifier)",    icon: "📲" },
};

const COLUMNS = [
  { id: "backlog",     name: "Backlog",     color: "var(--col-backlog)" },
  { id: "todo",        name: "To Do",       color: "var(--col-todo)" },
  { id: "in_progress", name: "In Progress", color: "var(--col-progress)" },
  { id: "review",      name: "Review",      color: "var(--col-review)" },
  { id: "done",        name: "Done",        color: "var(--col-done)" },
];

const LABEL_COLOR = {
  collect: "var(--collector)", extract: "var(--analyzer)", persist: "var(--collector)",
  patterns: "var(--coach)", coach: "var(--coach)", safety: "var(--guardian)", notify: "var(--notifier)",
};

const QUICK_INPUTS = [
  { text: "Corri 5km em 32 minutos e bebi 2L de água", mode: "auto" },
  { text: "Como estão meus hábitos esta semana?", mode: "analysis" },
  { text: "Dormi 5h, me senti cansado", mode: "checkin" },
];

const AGENT_AVATAR = Object.fromEntries(
  Object.entries(AGENTS).map(([k, v]) => [k, v.icon])
);
