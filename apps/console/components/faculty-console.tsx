"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  Clock3,
  Code2,
  FileCheck2,
  Flag,
  GraduationCap,
  History,
  Inbox,
  Info,
  Layers3,
  LayoutDashboard,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  X,
} from "lucide-react";
import { cases, comparison, manifest, taxonomy } from "@/lib/data";
import { applyPatches, transition, validatePatches } from "@/lib/review";
import { safeHtml } from "@/lib/sanitize";
import {
  Action,
  Case,
  Edit,
  emptyWorkspace,
  getPayload,
  ReviewRequest,
  Workspace,
} from "@/lib/types";

const human = (s: string | null) =>
  s ? s.replaceAll("_", " ").replace(/^./, (a) => a.toUpperCase()) : "No content repair";
const when = (s: string) =>
  new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(s));
const displayValue = (v: string | string[]) => (Array.isArray(v) ? v.join(", ") : v);
const storageKey = `acadza-review-v1-${manifest.resultsHash}`;
const providerLabel =
  manifest.provider === "groq" ? "Groq" : manifest.provider === "gemini" ? "Gemini" : "Model";

function Content({ value }: { value: string }) {
  return <div className="academic-content" dangerouslySetInnerHTML={{ __html: safeHtml(value) }} />;
}
function Subject({ subject }: { subject: string }) {
  return (
    <span className={`subject-icon ${subject.toLowerCase()}`}>
      <BookOpen size={15} />
    </span>
  );
}
function StatusPill({ c }: { c: Case }) {
  const kind =
    c.decision.route === "no_change"
      ? "neutral"
      : c.decision.route === "auto_apply"
        ? "green"
        : "amber";
  return (
    <span className={`pill ${kind}`}>
      {c.decision.route === "no_change"
        ? "No change needed"
        : c.decision.route === "auto_apply"
          ? "Ready to apply"
          : "Faculty review"}
    </span>
  );
}

export default function FacultyConsole() {
  const [activeId, setActiveId] = useState(
    cases.find((c) => c.reports.some((r) => r.reportId === "R001"))!.id,
  );
  const [section, setSection] = useState("queue");
  const [tab, setTab] = useState("question");
  const [filter, setFilter] = useState("all");
  const [subject, setSubject] = useState("all");
  const [query, setQuery] = useState("");
  const [workspace, setWorkspace] = useState<Workspace>(emptyWorkspace);
  const [storage, setStorage] = useState("connecting");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState<"edit" | "reject" | null>(null);
  const [draft, setDraft] = useState<Edit[]>([]);
  const [reason, setReason] = useState("");
  const [showSource, setShowSource] = useState(false);
  const [replyId, setReplyId] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const active = cases.find((c) => c.id === activeId)!;
  const review = workspace.reviews[activeId];
  const patches = review?.status === "draft" ? review.patches : active.patches;
  const settled = review && review.status !== "draft";
  const pending = cases.filter(
    (c) => !workspace.reviews[c.id] || workspace.reviews[c.id].status === "draft",
  ).length;
  const visible = useMemo(
    () =>
      cases.filter((c) => {
        const reviewed = workspace.reviews[c.id] && workspace.reviews[c.id].status !== "draft";
        const haystack = [
          c.title,
          c.question.subject,
          c.question.chapter,
          c.id,
          c.decision.repair,
          ...c.reports.map((r) => `${r.reportId} ${r.comment}`),
        ]
          .join(" ")
          .toLowerCase();
        return (
          (filter === "all" ||
            (filter === "pending" && !reviewed) ||
            (filter === "review" && c.decision.route === "faculty_review" && !reviewed) ||
            (filter === "ready" && c.decision.route === "auto_apply" && !reviewed) ||
            (filter === "closed" && reviewed)) &&
          (subject === "all" || c.question.subject === subject) &&
          haystack.includes(query.toLowerCase())
        );
      }),
    [filter, subject, query, workspace],
  );

  useEffect(() => {
    let cancelled = false;
    fetch("/api/workspace", { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        if (cancelled) return;
        if (data.storage === "database") {
          setWorkspace(data.state);
          setStorage("database");
        } else {
          const saved = localStorage.getItem(storageKey);
          if (saved) {
            const parsed = JSON.parse(saved);
            if (
              !Number.isInteger(parsed.version) ||
              !Array.isArray(parsed.audit) ||
              !parsed.reviews
            )
              throw new Error("Saved sandbox data is invalid");
            setWorkspace(parsed);
          }
          setStorage("browser");
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setStorage("unavailable");
          setError(e.message || "Could not open review storage");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  useEffect(() => {
    const keyboard = (e: KeyboardEvent) => {
      if (modal || /INPUT|TEXTAREA|SELECT/.test((e.target as HTMLElement).tagName)) return;
      if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      }
      const index = visible.findIndex((c) => c.id === activeId);
      if (e.key === "j" && visible[index + 1]) select(visible[index + 1].id);
      if (e.key === "k" && index > 0) select(visible[index - 1].id);
    };
    window.addEventListener("keydown", keyboard);
    return () => window.removeEventListener("keydown", keyboard);
  }, [activeId, visible, modal]);
  function select(id: string) {
    setActiveId(id);
    setTab("question");
    setShowSource(false);
    setReplyId("");
    setError("");
  }
  async function act(action: Action, requested = patches) {
    setBusy(true);
    setError("");
    const request: ReviewRequest = {
      caseId: active.id,
      sourceHash: active.sourceHash,
      expectedVersion: workspace.version,
      action,
      patches: requested,
      reason,
      requestId: crypto.randomUUID(),
    };
    try {
      if (storage !== "browser" && storage !== "database")
        throw new Error("Review storage is not ready");
      let next: Workspace;
      if (storage === "database") {
        const response = await fetch("/api/workspace", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Review failed");
        next = data.state;
      } else {
        const saved = localStorage.getItem(storageKey);
        const current = saved ? JSON.parse(saved) : emptyWorkspace();
        next = transition(current, request, active, taxonomy);
        localStorage.setItem(storageKey, JSON.stringify(next));
      }
      setWorkspace(next);
      setModal(null);
      setReason("");
      setToast(
        action === "edit"
          ? "Draft saved. Review the updated diff before approval."
          : action === "reject"
            ? "Proposal rejected. Your reason is in the audit trail."
            : requested.length
              ? "Correction applied to your demo workspace. Audit recorded."
              : active.decision.verdict === "defect"
                ? "Finding accepted. Human-authored repair is still required."
                : "Finding confirmed. Audit recorded.",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action could not be saved");
    } finally {
      setBusy(false);
    }
  }
  function openEdit() {
    setDraft(structuredClone(patches));
    setReason("");
    setError("");
    setModal("edit");
  }
  const after = (() => {
    try {
      return applyPatches(active.question, patches);
    } catch {
      return active.question;
    }
  })();
  const selectedReply = active.reports.find((r) => r.reportId === replyId) || active.reports[0];
  const currentIndex = visible.findIndex((c) => c.id === active.id);
  const activeAudit = workspace.audit.filter((a) => a.caseId === activeId);

  return (
    <div className="app-shell">
      <aside className="rail">
        <a className="brand-mark" href="/" aria-label="Acadza home">
          <GraduationCap size={29} strokeWidth={1.8} />
        </a>
        <div className="rail-divider" />
        <button
          className={section === "queue" ? "rail-button selected" : "rail-button"}
          onClick={() => setSection("queue")}
          aria-label="Report queue"
          title="Report queue"
        >
          <Inbox size={21} />
        </button>
        <button
          className={section === "history" ? "rail-button selected" : "rail-button"}
          onClick={() => setSection("history")}
          aria-label="Audit history"
          title="Audit history"
        >
          <History size={21} />
          <span className="rail-dot" hidden={!workspace.audit.length} />
        </button>
        <button
          className={section === "run" ? "rail-button selected" : "rail-button"}
          onClick={() => setSection("run")}
          aria-label="Run details"
          title="Run details"
        >
          <ShieldCheck size={21} />
        </button>
        <div className="rail-bottom">
          <span className="avatar">F</span>
          <span className="rail-small">FACULTY</span>
        </div>
      </aside>

      <div className="workspace-shell">
        <header className="topbar">
          <div className="wordmark">
            Acadza<span> / </span>
            <span className="workspace-name">Review room</span>
          </div>
          <div className="topbar-right">
            <span className="live-dot" />{" "}
            {manifest.mode === "live" ? `${providerLabel} results` : "Reviewed snapshot"}
            <span className="topbar-divider" />
            <span className="demo-tag">DEMO WORKSPACE</span>
          </div>
        </header>
        <div className="page-heading">
          <div>
            <div className="eyebrow">THE REPORT → FIX LOOP</div>
            <h1>
              A careful second look<span>.</span>
            </h1>
            <p>Less time sorting reports. More time getting the learning right.</p>
          </div>
          <div className="heading-note">
            <ShieldCheck size={17} />
            <span>
              Every change checked.
              <br />
              <strong>Every decision traceable.</strong>
            </span>
          </div>
        </div>
        <div className="summary-row">
          <button
            onClick={() => {
              setSection("queue");
              setFilter("all");
            }}
          >
            <span className="summary-icon">
              <Layers3 size={19} />
            </span>
            <span>
              <strong>{cases.length}</strong> grouped cases
            </span>
            <span className="summary-sub">from {manifest.reportCount} student reports</span>
          </button>
          <button
            onClick={() => {
              setSection("queue");
              setFilter("review");
            }}
          >
            <span className="summary-icon amber-icon">
              <Flag size={19} />
            </span>
            <span>
              <strong>
                {
                  cases.filter(
                    (c) => c.decision.route === "faculty_review" && !workspace.reviews[c.id],
                  ).length
                }
              </strong>{" "}
              need a closer look
            </span>
            <ArrowUpRight size={16} />
          </button>
          <button
            onClick={() => {
              setSection("queue");
              setFilter("ready");
            }}
          >
            <span className="summary-icon green-icon">
              <CheckCheck size={19} />
            </span>
            <span>
              <strong>
                {
                  cases.filter((c) => c.decision.route === "auto_apply" && !workspace.reviews[c.id])
                    .length
                }
              </strong>{" "}
              ready to apply
            </span>
            <ArrowUpRight size={16} />
          </button>
          <button onClick={() => setSection("history")}>
            <span className="summary-icon">
              <History size={19} />
            </span>
            <span>
              <strong>{workspace.audit.length}</strong> review actions
            </span>
            <span className="summary-sub">in your workspace</span>
          </button>
        </div>

        {section === "queue" ? (
          <div className="review-layout">
            <section className="queue-panel" aria-label="Grouped report queue">
              <div className="queue-heading">
                <h2>
                  Report queue <span>{visible.length}</span>
                </h2>
                <span className="tiny muted">{pending} open</span>
              </div>
              <label className="search-box">
                <Search size={16} />
                <input
                  ref={searchRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search question, report, topic…"
                  aria-label="Search reports"
                />
                <kbd>/</kbd>
              </label>
              <div className="queue-filters">
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  aria-label="Filter cases"
                >
                  <option value="all">All cases</option>
                  <option value="pending">Open cases</option>
                  <option value="review">Faculty review</option>
                  <option value="ready">Ready to apply</option>
                  <option value="closed">Reviewed</option>
                </select>
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  aria-label="Filter subject"
                >
                  <option value="all">All subjects</option>
                  <option>Physics</option>
                  <option>Botany</option>
                  <option>Zoology</option>
                </select>
              </div>
              <div className="sort-label">
                <ArrowDown size={12} /> Academic impact · reports · oldest first
                <span title="Scoring and answerability risks first; then distinct reports and age. No impression data is available.">
                  <Info size={12} />
                </span>
              </div>
              <div className="queue-list">
                {visible.map((c) => (
                  <button
                    className={`case-card ${activeId === c.id ? "active" : ""}`}
                    key={c.id}
                    onClick={() => select(c.id)}
                  >
                    <div className="case-card-meta">
                      <Subject subject={c.question.subject} />
                      <span>{c.question.subject}</span>
                      <span className="case-reference">
                        {c.reports[0].reportId}
                        {c.reports.length > 1 ? ` +${c.reports.length - 1}` : ""}
                      </span>
                      {workspace.reviews[c.id] && <CircleCheck size={14} className="green-text" />}
                    </div>
                    <h3>{c.title}</h3>
                    <div className="case-card-bottom">
                      <span className={`case-kind ${c.priority === 3 ? "high" : ""}`}>
                        <span />
                        {human(c.decision.repair || c.decision.verdict)}
                      </span>
                      <span>
                        <MessageSquare size={12} />
                        {c.reports.length}
                      </span>
                    </div>
                  </button>
                ))}
                {!visible.length && (
                  <div className="empty-state">
                    <Search size={28} />
                    <strong>No cases here</strong>
                    <p>Try another search or filter.</p>
                    <button
                      className="text-button"
                      onClick={() => {
                        setFilter("all");
                        setQuery("");
                        setSubject("all");
                      }}
                    >
                      Clear filters
                    </button>
                  </div>
                )}
              </div>
              <div className="queue-footer">
                <kbd>J</kbd>
                <kbd>K</kbd> to move through cases <ShieldCheck size={13} />
              </div>
            </section>

            <section className="detail-panel" aria-label="Case details">
              <div className="detail-toolbar">
                <span>
                  <Subject subject={active.question.subject} />
                  {active.question.subject}
                  <ChevronRight size={13} />
                  <span className="chapter-label">{active.question.chapter}</span>
                </span>
                <div className="case-pagination">
                  <span>
                    {currentIndex >= 0 ? currentIndex + 1 : "—"} / {visible.length}
                  </span>
                  <button
                    aria-label="Previous case"
                    disabled={currentIndex <= 0}
                    onClick={() => select(visible[currentIndex - 1].id)}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    aria-label="Next case"
                    disabled={currentIndex < 0 || currentIndex >= visible.length - 1}
                    onClick={() => select(visible[currentIndex + 1].id)}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
              <div className="case-heading">
                <div className="case-overline">
                  <span className={`priority-dot p${active.priority}`} />
                  {active.urgencyReason}
                  <span className="muted">
                    · {active.reports.length} {active.reports.length === 1 ? "report" : "reports"}
                  </span>
                </div>
                <div className="case-title-row">
                  <h2>{human(active.decision.repair || active.decision.verdict)}</h2>
                  <StatusPill c={active} />
                </div>
                <div className="case-identifiers">
                  <span>{active.reports.map((r) => r.reportId).join(" · ")}</span>
                  <span>
                    {human(active.question.questionType)}
                    <span className="identifier-separator">/</span>Oldest report{" "}
                    {when(active.oldestReport)} IST
                  </span>
                </div>
              </div>
              {review && (
                <div className="review-banner">
                  <CircleCheck size={16} />
                  <span>
                    {review.status === "draft"
                      ? "Edited draft saved. Approval is still required."
                      : review.status === "needs_authoring"
                        ? "Finding accepted. Awaiting a faculty-authored repair."
                        : `Proposal ${review.status} in your demo workspace.`}
                  </span>
                  <button onClick={() => setTab("audit")}>
                    View record <ArrowRight size={12} />
                  </button>
                </div>
              )}
              <nav className="detail-tabs" aria-label="Case views">
                {[
                  ["question", "Question", BookOpen],
                  ["diff", "Proposed change", FileCheck2],
                  ["reports", "Reports", MessageSquare],
                  ["audit", "Audit trail", History],
                ].map(([key, label, Icon]) => {
                  const TabIcon = Icon as typeof BookOpen;
                  return (
                    <button
                      key={key as string}
                      className={tab === key ? "active" : ""}
                      onClick={() => setTab(key as string)}
                    >
                      <TabIcon size={14} />
                      {label as string}
                      {key === "reports" && <span>{active.reports.length}</span>}
                    </button>
                  );
                })}
              </nav>
              <div className="detail-scroll" key={`${activeId}-${tab}`}>
                {tab === "question" && (
                  <>
                    <div className="section-label">
                      {review?.status === "approved"
                        ? "CURRENT WORKSPACE QUESTION"
                        : "QUESTION AS STORED"}
                      <button className="text-button" onClick={() => setShowSource(!showSource)}>
                        <Code2 size={13} />
                        {showSource ? "Rendered view" : "Source view"}
                      </button>
                    </div>
                    {showSource ? (
                      <pre className="source-block">{getPayload(active.question).question}</pre>
                    ) : (
                      <Content
                        value={
                          getPayload(
                            review?.status === "approved" ? review.question : active.question,
                          ).question
                        }
                      />
                    )}
                    <div className="answer-strip">
                      <span>Stored answer</span>
                      <strong>
                        {displayValue(
                          getPayload(
                            review?.status === "approved" ? review.question : active.question,
                          ).answer,
                        )}
                      </strong>
                      {active.decision.repair === "answer_key" && patches.length > 0 && (
                        <>
                          <ArrowRight size={15} />
                          <span>Proposed</span>
                          <strong className="green-text">
                            {displayValue(
                              patches.find((p) => p.field === "answer")?.replace || "—",
                            )}
                          </strong>
                        </>
                      )}
                    </div>
                    <details className="solution-disclosure">
                      <summary>
                        <BookOpen size={15} /> Stored solution <ChevronDown size={15} />
                      </summary>
                      <Content value={getPayload(active.question).solution} />
                    </details>
                    <div className="student-lead">
                      <div className="section-label">
                        <MessageSquare size={13} /> THE STUDENT'S LEAD
                      </div>
                      <blockquote>“{active.reports[0].comment}”</blockquote>
                      <span>
                        {active.reports[0].reportId} · {active.reports[0].source} ·{" "}
                        {when(active.reports[0].reportedAt)} IST
                      </span>
                    </div>
                    {active.question.errorHistory.length > 0 && (
                      <div className="history-note">
                        <History size={16} />
                        <div>
                          <strong>Existing faculty history</strong>
                          {active.question.errorHistory.map((h, i) => (
                            <p key={i}>
                              {h.note}
                              <br />
                              <span className="muted">
                                {when(h.at)} IST · {h.actor}
                              </span>
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
                {tab === "diff" && (
                  <>
                    <div className="section-label">
                      EXACT PROPOSED CHANGES
                      <span>
                        {patches.length} {patches.length === 1 ? "edit" : "edits"}
                      </span>
                    </div>
                    {patches.length ? (
                      patches.map((p, i) => (
                        <div className="patch-card" key={i}>
                          <div className="patch-heading">
                            <FileCheck2 size={15} />
                            <strong>{human(p.field)}</strong>
                            <span>
                              Exact replacement · {i + 1} of {patches.length}
                            </span>
                          </div>
                          <div className="diff-line removed">
                            <span>−</span>
                            <code>{displayValue(p.find)}</code>
                          </div>
                          <div className="diff-line added">
                            <span>+</span>
                            <code>{displayValue(p.replace)}</code>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="no-patch">
                        <ShieldCheck size={27} />
                        <h3>
                          {active.decision.verdict === "defect"
                            ? "A finding, without a guessed fix."
                            : "No content change proposed."}
                        </h3>
                        <p>
                          {active.decision.verdict === "defect"
                            ? "The supplied evidence does not support a safe machine patch. Faculty can accept the finding and arrange the original content or an authored repair."
                            : "The reported issue does not require changing this question's stored content."}
                        </p>
                      </div>
                    )}
                    {patches.length > 0 && (
                      <>
                        <div className="section-label preview-label">RENDERED PREVIEW</div>
                        <div className="preview-grid">
                          <div>
                            <span className="preview-tag">BEFORE</span>
                            {patches.some((p) => p.field === "solution") ? (
                              <Content value={getPayload(active.question).solution} />
                            ) : patches.every((p) => p.field === "answer") ? (
                              <div className="large-key">
                                {displayValue(getPayload(active.question).answer)}
                              </div>
                            ) : (
                              <Content value={getPayload(active.question).question} />
                            )}
                          </div>
                          <div>
                            <span className="preview-tag green-text">AFTER</span>
                            {patches.some((p) => p.field === "solution") ? (
                              <Content value={getPayload(after).solution} />
                            ) : patches.every((p) => p.field === "answer") ? (
                              <div className="large-key green-text">
                                {displayValue(getPayload(after).answer)}
                              </div>
                            ) : (
                              <Content value={getPayload(after).question} />
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </>
                )}
                {tab === "reports" && (
                  <>
                    <div className="section-label">
                      {active.reports.length} REPORTS · ONE SHARED CONTENT REVIEW
                    </div>
                    {active.reports.map((r) => (
                      <article className="report-card" key={r.reportId}>
                        <div>
                          <span className="mini-avatar">S</span>
                          <strong>{r.reportId}</strong>
                          <span className="pill neutral">{r.source}</span>
                          <time>{when(r.reportedAt)} IST</time>
                        </div>
                        <p>{r.comment}</p>
                        <div className="report-reply">
                          <MessageSquare size={14} />
                          <span>{active.replies[r.reportId]}</span>
                        </div>
                      </article>
                    ))}
                    <p className="inline-note">
                      <Info size={14} />
                      Report count affects urgency. It does not prove the proposed answer.
                    </p>
                  </>
                )}
                {tab === "audit" && (
                  <>
                    <div className="section-label">
                      CASE HISTORY<span>{activeAudit.length} review actions</span>
                    </div>
                    <div className="timeline">
                      <div className="timeline-event">
                        <span className="timeline-dot">
                          <Sparkles size={12} />
                        </span>
                        <strong>
                          {manifest.mode === "live"
                            ? `${providerLabel} triage generated`
                            : "Reviewed baseline generated"}
                        </strong>
                        <time>{when(manifest.generatedAt)} IST</time>
                        <p>{manifest.disclosure}</p>
                        <span className="hash-label">
                          Source version {active.sourceHash.slice(0, 12)}
                        </span>
                      </div>
                      {activeAudit.map((a) => (
                        <div className="timeline-event" key={a.id}>
                          <span className="timeline-dot">
                            <Check size={12} />
                          </span>
                          <strong>
                            {human(a.action)} · {a.actor}
                          </strong>
                          <time>{when(a.at)} IST</time>
                          <p>{a.reason}</p>
                          <span className="hash-label">
                            {a.patches.length} proposed edits · {a.id.slice(0, 8)}
                          </span>
                        </div>
                      ))}
                    </div>
                    {!activeAudit.length && (
                      <p className="inline-note">
                        No faculty action yet. Approve, edit, or reject to create the first entry.
                      </p>
                    )}
                  </>
                )}
              </div>
              <footer className="review-actions">
                <div>
                  <ShieldCheck size={14} />
                  <span>
                    {storage === "database"
                      ? "Saved to your persistent demo workspace"
                      : storage === "browser"
                        ? "Browser sandbox · saved on this device"
                        : storage === "connecting"
                          ? "Opening review storage…"
                          : "Review storage unavailable"}
                  </span>
                </div>
                {error && !modal && (
                  <p className="action-error" role="alert">
                    {error}
                  </p>
                )}
                <div className="action-buttons">
                  <button
                    className="button ghost danger"
                    onClick={() => {
                      setReason("");
                      setModal("reject");
                    }}
                    disabled={!!settled || busy || !["browser", "database"].includes(storage)}
                  >
                    <X size={15} />
                    Reject
                  </button>
                  <button
                    className="button secondary"
                    onClick={openEdit}
                    disabled={!!settled || !patches.length || busy}
                  >
                    <Pencil size={14} />
                    Edit proposal
                  </button>
                  <button
                    className="button primary"
                    onClick={() => act("approve")}
                    disabled={!!settled || busy || !["browser", "database"].includes(storage)}
                  >
                    {busy ? <Loader2 size={15} className="spin" /> : <Check size={16} />}
                    {settled
                      ? "Review recorded"
                      : patches.length
                        ? "Approve correction"
                        : "Approve finding"}
                  </button>
                </div>
              </footer>
            </section>

            <aside className="insight-panel">
              <div className="insight-title">
                <span className="ai-icon">
                  <Sparkles size={17} />
                </span>
                <h2>The second look</h2>
                <span className="tiny muted">AI ASSISTED</span>
              </div>
              <div className="verdict-box">
                <div className="section-label">FINDING</div>
                <h3>
                  {active.decision.verdict === "defect"
                    ? "A real issue to address"
                    : human(active.decision.verdict)}
                </h3>
                <p>{taxonomy.verdicts[active.decision.verdict]}</p>
              </div>
              <div className="evidence-box">
                <div className="section-label">WHY THIS DECISION</div>
                <p>{active.decision.evidence}</p>
              </div>
              <div className="checks-box">
                <div className="section-label">VERIFICATION</div>
                {manifest.mode === "live" && active.model && (
                  <div className="check-row muted">
                    <Info size={14} />
                    <span>Case model: {active.model}</span>
                  </div>
                )}
                <div className="check-row">
                  <ShieldCheck size={15} />
                  <span>
                    {active.validation.passed
                      ? "Patch scope checked"
                      : "Patch blocked by validation"}
                  </span>
                </div>
                {active.checks.map((c) => (
                  <details key={c.id}>
                    <summary>
                      <CircleCheck size={14} />
                      <span>{human(c.id)} calculation</span>
                      <ChevronDown size={12} />
                    </summary>
                    <p>{c.evidence}</p>
                  </details>
                ))}
                {active.blindSolves.map((s, i) => (
                  <details key={i}>
                    <summary>
                      <BookOpen size={14} />
                      Blind solve {i + 1}
                      <ChevronDown size={12} />
                    </summary>
                    <p>
                      Answer:{" "}
                      {Array.isArray(s.answer)
                        ? s.answer.join(", ")
                        : (s.answer ?? "Insufficient data")}
                    </p>
                    <p>{s.derivation}</p>
                  </details>
                ))}
                {!active.checks.length && !active.blindSolves.length && (
                  <div className="check-row muted">
                    <Info size={14} />
                    <span>Reviewed text and source evidence</span>
                  </div>
                )}
                <p className="confidence-note">
                  Evidence rating {active.decision.confidence.toFixed(2)} · uncalibrated
                  <br />A review signal, not a probability of correctness.
                </p>
              </div>
              <div className="reply-box">
                <div className="section-label">
                  <MessageSquare size={13} />
                  STUDENT REPLY PREVIEW
                </div>
                {active.reports.length > 1 && (
                  <select
                    aria-label="Reply report"
                    value={selectedReply.reportId}
                    onChange={(e) => setReplyId(e.target.value)}
                  >
                    {active.reports.map((r) => (
                      <option key={r.reportId}>{r.reportId}</option>
                    ))}
                  </select>
                )}
                <p>{active.replies[selectedReply.reportId]}</p>
                <span className="tiny muted">Preview only · no message is sent</span>
              </div>
              <div className="guard-note">
                <ShieldCheck size={16} />
                <p>
                  {active.decision.repair && !taxonomy.repairs[active.decision.repair]?.auto
                    ? "Faculty-only repair. The engine cannot author or apply this content."
                    : active.decision.route === "faculty_review"
                      ? "Held for review. No automatic change has been made."
                      : "Proposals are checked before a change reaches the demo question store."}
                </p>
              </div>
            </aside>
          </div>
        ) : section === "history" ? (
          <section className="full-panel">
            <div className="full-panel-heading">
              <div>
                <div className="eyebrow">ACCOUNTABILITY, BUILT IN</div>
                <h2>Every decision has a history.</h2>
                <p>
                  Faculty actions in your {storage === "database" ? "persistent" : "browser"} demo
                  workspace.
                </p>
              </div>
              <button className="button secondary" onClick={() => setSection("queue")}>
                <ArrowLeft size={15} />
                Back to queue
              </button>
            </div>
            {workspace.audit.length ? (
              <div className="audit-table">
                <div className="audit-table-head">
                  <span>Case</span>
                  <span>Action</span>
                  <span>Reason</span>
                  <span>Recorded at · IST</span>
                </div>
                {workspace.audit.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => {
                      select(a.caseId);
                      setTab("audit");
                      setSection("queue");
                    }}
                  >
                    <span>
                      {cases.find((c) => c.id === a.caseId)?.reports[0].reportId}
                      <small>
                        {human(cases.find((c) => c.id === a.caseId)?.decision.repair || "Finding")}
                      </small>
                    </span>
                    <span className="green-text">{human(a.action)}</span>
                    <span>{a.reason}</span>
                    <time>{when(a.at)}</time>
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-state roomy">
                <History size={34} />
                <h3>A clean slate.</h3>
                <p>
                  Your first review will appear here with its reason, exact proposal, and content
                  versions.
                </p>
              </div>
            )}
          </section>
        ) : (
          <section className="full-panel run-panel">
            <div className="eyebrow">HONEST BY DESIGN</div>
            <h2>What produced this queue?</h2>
            <p className="run-disclosure">{manifest.disclosure}</p>
            <div className="run-grid">
              <div>
                <span>Run mode</span>
                <strong>{manifest.mode}</strong>
              </div>
              <div>
                <span>Report coverage</span>
                <strong>{manifest.reportCount} / 44</strong>
              </div>
              <div>
                <span>Grouped questions</span>
                <strong>{manifest.questionCount}</strong>
              </div>
              <div>
                <span>API calls in this run</span>
                <strong>{manifest.apiCallsThisRun}</strong>
              </div>
              <div>
                <span>Model</span>
                <strong>{manifest.model || "No external model run"}</strong>
              </div>
              <div>
                <span>Review storage</span>
                <strong>{storage === "database" ? "PostgreSQL" : "Browser sandbox"}</strong>
              </div>
            </div>
            {manifest.mode === "reviewed" && (
              <div className="run-comparison">
                <div className="run-comparison-heading">
                  <Sparkles size={17} />
                  <strong>Completed Groq cross-check</strong>
                  <span>{comparison.reportCount} reports</span>
                </div>
                <p>
                  {comparison.verdictRepairAgreement}/{comparison.reportCount} verdict and repair
                  pairs match this reviewed snapshot. {comparison.routeDifferenceIds.length} routes
                  and {comparison.editDifferenceIds.length} edits differ; the reviewed version keeps
                  the fuller supported edit previews.
                </p>
                <small>Agreement between artifacts is not hidden-ground-truth accuracy.</small>
              </div>
            )}
            <p>{manifest.confidenceMeaning}</p>
            <div className="run-warning">
              <Info size={18} />
              <p>
                Coverage and validation checks do not establish accuracy against Acadza's hidden
                ground truth. This workspace changes demonstration data only.
              </p>
            </div>
            <div className="hash-block">
              <span>Results artifact SHA-256</span>
              <code>{manifest.resultsHash}</code>
              <span>Generated</span>
              <code>{when(manifest.generatedAt)} IST</code>
            </div>
          </section>
        )}
        <footer className="page-footer">
          <span>Built for the people behind better questions.</span>
          <span>
            <span className="live-dot" />{" "}
            {manifest.mode === "live" ? "Precomputed model run" : "Precomputed reviewed findings"} ·{" "}
            {storage === "database" ? "Persistent review workspace" : "Browser sandbox"}
          </span>
        </footer>
      </div>

      {toast && (
        <div className="toast" role="status">
          <CircleCheck size={19} />
          <span>{toast}</span>
          <button onClick={() => setToast("")} aria-label="Dismiss notification">
            <X size={15} />
          </button>
        </div>
      )}
      {modal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !busy) setModal(null);
          }}
        >
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div className="modal-heading">
              <div>
                <div className="eyebrow">FACULTY REVIEW · {active.reports[0].reportId}</div>
                <h2 id="modal-title">
                  {modal === "edit" ? "Make the correction precise." : "Why reject this proposal?"}
                </h2>
              </div>
              <button aria-label="Close dialog" onClick={() => setModal(null)}>
                <X size={20} />
              </button>
            </div>
            {modal === "edit" && (
              <>
                <p className="muted">
                  Save an edited draft, then inspect its diff before approving. Only permitted
                  fields can change.
                </p>
                {draft.map((p, i) => (
                  <div className="edit-patch" key={i}>
                    <label>
                      Field
                      <select
                        value={p.field}
                        onChange={(e) => {
                          const field = e.target.value as Edit["field"];
                          const original =
                            field === "questionType"
                              ? active.question.questionType
                              : getPayload(active.question)[field];
                          setDraft((d) =>
                            d.map((x, n) =>
                              n === i ? { field, find: original, replace: original } : x,
                            ),
                          );
                        }}
                      >
                        {(taxonomy.repairs[active.decision.repair!]?.fields || []).map((f) => (
                          <option key={f}>{f}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Find exactly
                      <textarea
                        value={Array.isArray(p.find) ? JSON.stringify(p.find) : p.find}
                        onChange={(e) =>
                          setDraft((d) =>
                            d.map((x, n) =>
                              n === i ? { ...x, find: parseEditValue(e.target.value, p.find) } : x,
                            ),
                          )
                        }
                      />
                    </label>
                    <label>
                      Replace with
                      <textarea
                        value={Array.isArray(p.replace) ? JSON.stringify(p.replace) : p.replace}
                        onChange={(e) =>
                          setDraft((d) =>
                            d.map((x, n) =>
                              n === i
                                ? { ...x, replace: parseEditValue(e.target.value, p.replace) }
                                : x,
                            ),
                          )
                        }
                      />
                    </label>
                  </div>
                ))}
                <p className="inline-note">
                  Source text is preserved. Mathematical or substantive revisions need faculty
                  verification; structural checks do not prove academic correctness.
                </p>
              </>
            )}
            <label className="reason-label">
              {modal === "edit" ? "What changed, and why?" : "Your reason"}
              <textarea
                autoFocus={modal === "reject"}
                value={reason}
                maxLength={800}
                onChange={(e) => setReason(e.target.value)}
                placeholder={
                  modal === "edit"
                    ? "Explain the correction for the next reviewer…"
                    : "Explain what the proposal missed…"
                }
              />
            </label>
            {modal === "edit" && validatePatches(active, draft, taxonomy).length > 0 && (
              <div className="action-error">
                {validatePatches(active, draft, taxonomy).join(" · ")}
              </div>
            )}
            {error && (
              <p className="action-error" role="alert">
                {error}
              </p>
            )}
            <div className="modal-actions">
              <button className="button secondary" onClick={() => setModal(null)}>
                Cancel
              </button>
              <button
                className="button primary"
                disabled={
                  busy ||
                  !reason.trim() ||
                  (modal === "edit" && validatePatches(active, draft, taxonomy).length > 0)
                }
                onClick={() =>
                  act(modal === "edit" ? "edit" : "reject", modal === "edit" ? draft : patches)
                }
              >
                {busy ? (
                  <Loader2 size={15} className="spin" />
                ) : modal === "edit" ? (
                  <Pencil size={14} />
                ) : (
                  <X size={14} />
                )}
                {modal === "edit" ? "Save reviewed draft" : "Record rejection"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function parseEditValue(value: string, old: string | string[]): string | string[] {
  if (Array.isArray(old)) {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) && parsed.every((x) => typeof x === "string") ? parsed : value;
    } catch {
      return value;
    }
  }
  return value;
}
