"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import sourceQuestions from "./question-bank.json";

type QuestionType = "单选题" | "多选题" | "判断题" | "简答题";
type Difficulty = "基础" | "进阶" | "困难";
type Status = "已发布" | "待审核" | "草稿";
type OptionKey = "A" | "B" | "C" | "D";

type Question = {
  id: string;
  code: string;
  title: string;
  image: string;
  options: Record<OptionKey, string>;
  type: QuestionType;
  category: string;
  section: string;
  difficulty: Difficulty;
  answer: string;
  explanation: string;
  detailedExplanation: string;
  tags: string[];
  status: Status;
  updatedAt: string;
};

const STORAGE_KEY = "pingan-question-bank-v9";
const LEGACY_STORAGE_KEY = "pingan-question-bank-v8";
const PAGE_SIZE = 50;
const OPTION_KEYS: OptionKey[] = ["A", "B", "C", "D"];
const seedQuestions = sourceQuestions as Question[];
const refreshedSeedImages = new Map(
  seedQuestions
    .filter((question) => ["B01", "B02", "B03", "B04", "B05", "B06", "L01"].includes(question.section))
    .map((question) => [question.code, question.image]),
);

const blankQuestion = (): Question => ({
  id: crypto.randomUUID(),
  code: "",
  title: "",
  image: "",
  options: { A: "", B: "", C: "", D: "" },
  type: "单选题",
  category: "B 类题目",
  section: "自建",
  difficulty: "基础",
  answer: "",
  explanation: "",
  detailedExplanation: "",
  tags: [],
  status: "草稿",
  updatedAt: new Date().toISOString().slice(0, 10),
});

function csvEscape(value: string) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function statusClass(status: Status) {
  return status === "已发布" ? "published" : status === "待审核" ? "review" : "draft";
}

function normalizeQuestion(item: Partial<Question>, index: number): Question {
  const fallback = blankQuestion();
  return {
    ...fallback,
    ...item,
    id: item.id || crypto.randomUUID(),
    code: item.code || `IMP-${String(index + 1).padStart(4, "0")}`,
    image: item.image || "",
    options: { ...fallback.options, ...(item.options || {}) },
    category: item.category || "自建题目",
    section: item.section || "自建",
    explanation: item.explanation || "",
    detailedExplanation: item.detailedExplanation || "",
    tags: Array.isArray(item.tags) ? item.tags : [],
    updatedAt: item.updatedAt || new Date().toISOString().slice(0, 10),
  };
}

function answerText(question: Question) {
  const keys = question.answer.split(/[、,，\s]+/).filter(Boolean) as OptionKey[];
  const labels = keys.map((key) => question.options[key]).filter(Boolean);
  return labels.length ? `${question.answer} · ${labels.join("；")}` : question.answer;
}

export default function Home() {
  const [questions, setQuestions] = useState<Question[]>(seedQuestions);
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("全部题型");
  const [categoryFilter, setCategoryFilter] = useState("全部分类");
  const [sectionFilter, setSectionFilter] = useState("全部章节");
  const [statusFilter, setStatusFilter] = useState("全部状态");
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<"review" | "table">("review");
  const [editor, setEditor] = useState<Question | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [toast, setToast] = useState("");
  const [quiz, setQuiz] = useState<Question[]>([]);
  const [zoomImage, setZoomImage] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
    if (saved) {
      try {
        const incoming = JSON.parse(saved) as Partial<Question>[];
        if (Array.isArray(incoming)) {
          const normalized = incoming.map(normalizeQuestion).map((question) => ({
            ...question,
            image: refreshedSeedImages.get(question.code) || question.image,
          }));
          const storedCodes = new Set(normalized.map((question) => question.code));
          const newLightingQuestions = seedQuestions.filter(
            (question) => question.section === "L01" && !storedCodes.has(question.code),
          );
          setQuestions([...normalized, ...newLightingQuestions]);
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(LEGACY_STORAGE_KEY);
      }
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(questions));
      } catch {
        setToast("浏览器存储空间不足，请先导出备份");
      }
    }
  }, [questions, ready]);

  useEffect(() => setPage(1), [query, typeFilter, categoryFilter, sectionFilter, statusFilter]);

  const categories = useMemo(
    () => [...new Set(questions.map((question) => question.category))].sort(),
    [questions],
  );
  const sections = useMemo(
    () => [...new Set(questions.map((question) => question.section))].sort(),
    [questions],
  );

  const visibleQuestions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return questions.filter((question) => {
      const haystack = [
        question.code,
        question.title,
        question.answer,
        question.explanation,
        question.detailedExplanation,
        question.section,
        ...Object.values(question.options),
        ...question.tags,
      ].join(" ").toLowerCase();
      return (
        (!needle || haystack.includes(needle)) &&
        (typeFilter === "全部题型" || question.type === typeFilter) &&
        (categoryFilter === "全部分类" || question.category === categoryFilter) &&
        (sectionFilter === "全部章节" || question.section === sectionFilter) &&
        (statusFilter === "全部状态" || question.status === statusFilter)
      );
    });
  }, [questions, query, typeFilter, categoryFilter, sectionFilter, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(visibleQuestions.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedQuestions = visibleQuestions.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const flash = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2400);
  };

  const resetFilters = () => {
    setQuery("");
    setTypeFilter("全部题型");
    setCategoryFilter("全部分类");
    setSectionFilter("全部章节");
    setStatusFilter("全部状态");
  };

  const startNew = () => {
    const item = blankQuestion();
    item.code = `NEW-${String(questions.length + 1).padStart(4, "0")}`;
    setEditor(item);
    setIsNew(true);
  };

  const saveQuestion = (event: FormEvent) => {
    event.preventDefault();
    if (!editor || !editor.title.trim() || !editor.answer.trim()) return;
    const saved = { ...editor, updatedAt: new Date().toISOString().slice(0, 10) };
    setQuestions((current) =>
      isNew ? [saved, ...current] : current.map((item) => (item.id === saved.id ? saved : item)),
    );
    setEditor(null);
    flash(isNew ? "新题已添加" : "题目已更新");
  };

  const deleteQuestion = () => {
    if (!editor || !window.confirm(`确定删除 ${editor.code} 吗？`)) return;
    setQuestions((current) => current.filter((item) => item.id !== editor.id));
    setEditor(null);
    flash("题目已删除");
  };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(questions, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `理论题库-审核包-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
    flash("审核包已导出，可交给 Codex 批量修改");
  };

  const exportCsv = () => {
    const headers = ["编号", "题干", "图片", "选项A", "选项B", "选项C", "选项D", "题型", "分类", "章节", "难度", "答案", "简析", "试题详解", "标签", "状态"];
    const rows = questions.map((item) => [
      item.code, item.title, item.image, item.options.A, item.options.B, item.options.C, item.options.D,
      item.type, item.category, item.section, item.difficulty, item.answer, item.explanation,
      item.detailedExplanation, item.tags.join("|"), item.status,
    ].map(csvEscape).join(","));
    const blob = new Blob(["\ufeff" + [headers.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `理论题库-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
    flash("CSV 已导出");
  };

  const importJson = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const incoming = JSON.parse(await file.text()) as Partial<Question>[];
      if (!Array.isArray(incoming)) throw new Error();
      const normalized = incoming.map(normalizeQuestion);
      setQuestions(normalized);
      flash(`已导入 ${normalized.length} 道题`);
    } catch {
      flash("导入失败：请选择本工具导出的 JSON 题库文件");
    } finally {
      event.target.value = "";
    }
  };

  const buildQuiz = () => {
    const source = visibleQuestions.filter((item) => item.status === "已发布");
    const shuffled = [...source];
    for (let index = shuffled.length - 1; index > 0; index -= 1) {
      const pick = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[pick]] = [shuffled[pick], shuffled[index]];
    }
    setQuiz(shuffled.slice(0, Math.min(10, shuffled.length)));
    if (!shuffled.length) flash("当前筛选结果中没有已发布题目");
  };

  const openEditor = (question: Question) => {
    setEditor({ ...question, options: { ...question.options }, tags: [...question.tags] });
    setIsNew(false);
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">平</span><div><strong>平安线题库</strong><small>KNOWLEDGE OPERATIONS</small></div></div>
        <nav aria-label="题库导航">
          <button className="nav-item active"><span>▦</span> 题目管理 <b>{questions.length}</b></button>
          <button className="nav-item" onClick={buildQuiz}><span>◇</span> 随机组卷</button>
          <button className="nav-item" onClick={() => fileInput.current?.click()}><span>⇧</span> 导入批改包</button>
          <button className="nav-item" onClick={exportJson}><span>⇩</span> 导出审核包</button>
        </nav>
        <div className="category-list">
          <p>题目大类</p>
          <button className={categoryFilter === "全部分类" ? "selected" : ""} onClick={() => setCategoryFilter("全部分类")}><span>全部题目</span><b>{questions.length}</b></button>
          {categories.map((category) => (
            <button key={category} className={categoryFilter === category ? "selected" : ""} onClick={() => setCategoryFilter(category)}>
              <span>{category}</span><b>{questions.filter((item) => item.category === category).length}</b>
            </button>
          ))}
        </div>
        <div className="sidebar-note"><span className="pulse" /><div><strong>浏览器安全保存</strong><small>增删改内容保存在当前浏览器，可随时导出备份</small></div></div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><p className="eyebrow">理论考核资产中心</p><h1>题目管理</h1></div>
          <div className="top-actions"><button className="ghost" onClick={exportCsv}>导出 CSV</button><button className="primary" onClick={startNew}><span>+</span> 新增题目</button></div>
        </header>

        <section className="metrics" aria-label="题库统计">
          <article><span>总题数</span><strong>{questions.length}</strong><small>Excel 完整题库</small></article>
          <article><span>带图题</span><strong>{questions.filter((q) => q.image).length}</strong><small>题图已压缩接入</small></article>
          <article><span>章节数</span><strong>{sections.length}</strong><small>支持章节筛选</small></article>
          <article><span>题目大类</span><strong>{categories.length}</strong><small>按编号前缀归类</small></article>
        </section>

        <section className="content-card">
          <div className="view-toolbar">
            <div><strong>检查视图</strong><span>大图按小程序 375px 内容宽度展示，可点击查看原图</span></div>
            <div className="view-switch"><button className={viewMode === "review" ? "active" : ""} onClick={() => setViewMode("review")}>▧ 大图审核</button><button className={viewMode === "table" ? "active" : ""} onClick={() => setViewMode("table")}>☷ 管理表格</button></div>
          </div>
          <div className="filters">
            <label className="search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索编号、题干、选项、答案或解析" /></label>
            <select aria-label="题型" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option>全部题型</option><option>单选题</option><option>多选题</option><option>判断题</option><option>简答题</option></select>
            <select aria-label="章节" value={sectionFilter} onChange={(event) => setSectionFilter(event.target.value)}><option>全部章节</option>{sections.map((section) => <option key={section}>{section}</option>)}</select>
            <select aria-label="状态" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>全部状态</option><option>已发布</option><option>待审核</option><option>草稿</option></select>
            <button className="icon-button" title="清空筛选" onClick={resetFilters}>↻</button>
          </div>

          {viewMode === "review" ? (
            <div className="review-grid">
              {pagedQuestions.map((question) => (
                <article className="review-card" key={question.id}>
                  <header><div><code>{question.code}</code><span>{question.section}</span></div><button onClick={() => openEditor(question)}>编辑</button></header>
                  <div className="miniapp-frame">
                    {question.image ? <button className="image-button" onClick={() => setZoomImage(question.image)} title="点击查看原图"><img src={question.image} alt={`${question.code} 题图`} loading="lazy" /></button> : <div className="no-image">本题无图片</div>}
                  </div>
                  <div className="review-copy"><h3>{question.title}</h3><div className="review-options">{OPTION_KEYS.filter((key) => question.options[key]).map((key) => <p key={key}><b>{key}</b>{question.options[key]}</p>)}</div><details><summary>答案与解析</summary><p><strong>{answerText(question)}</strong><br />{question.explanation}<br />{question.detailedExplanation}</p></details></div>
                </article>
              ))}
              {!visibleQuestions.length && <div className="empty"><strong>没有找到匹配题目</strong><span>请调整搜索词或筛选条件</span></div>}
            </div>
          ) : <div className="table-wrap">
            <table>
              <thead><tr><th>编号</th><th>题干</th><th>题型</th><th>大类 / 章节</th><th>状态</th><th>更新日期</th><th /></tr></thead>
              <tbody>
                {pagedQuestions.map((question) => (
                  <tr key={question.id} onDoubleClick={() => openEditor(question)}>
                    <td><code>{question.code}</code></td>
                    <td className="question-cell"><div className="question-summary">{question.image && <img src={question.image} alt="" loading="lazy" />}<div><strong>{question.title}</strong><small>{question.tags.map((tag) => `#${tag}`).join("  ")}</small></div></div></td>
                    <td><span className="type-pill">{question.type}</span></td>
                    <td><span className="category-name">{question.category}</span><small className="section-name">{question.section}</small></td>
                    <td><span className={`status ${statusClass(question.status)}`}><i />{question.status}</span></td>
                    <td>{question.updatedAt}</td>
                    <td><button className="edit-button" aria-label={`编辑 ${question.code}`} onClick={() => openEditor(question)}>编辑</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!visibleQuestions.length && <div className="empty"><strong>没有找到匹配题目</strong><span>请调整搜索词或筛选条件</span></div>}
          </div>}
          <footer className="table-footer">
            <span>当前筛选 {visibleQuestions.length} / {questions.length} 道题</span>
            <div className="pager"><button disabled={currentPage <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button><span>{currentPage} / {totalPages}</span><button disabled={currentPage >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>下一页</button></div>
          </footer>
        </section>
      </section>

      {editor && (
        <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditor(null); }}>
          <aside className="drawer" aria-label={isNew ? "新增题目" : "编辑题目"}>
            <div className="drawer-head"><div><p>{isNew ? "NEW QUESTION" : editor.code}</p><h2>{isNew ? "新增题目" : "编辑题目"}</h2></div><button onClick={() => setEditor(null)} aria-label="关闭">×</button></div>
            <form onSubmit={saveQuestion}>
              <div className="field-grid">
                <label><span>题目编号</span><input value={editor.code} onChange={(e) => setEditor({ ...editor, code: e.target.value })} required /></label>
                <label><span>题型</span><select value={editor.type} onChange={(e) => setEditor({ ...editor, type: e.target.value as QuestionType })}><option>单选题</option><option>多选题</option><option>判断题</option><option>简答题</option></select></label>
              </div>
              <label><span>题干 <em>*</em></span><textarea rows={4} value={editor.title} onChange={(e) => setEditor({ ...editor, title: e.target.value })} placeholder="请输入题目内容" required /></label>
              <label><span>题图地址</span><input value={editor.image} onChange={(e) => setEditor({ ...editor, image: e.target.value })} placeholder="可填写 https:// 图片地址" /></label>
              {editor.image && <img className="editor-image" src={editor.image} alt="题图预览" />}
              <div className="option-grid">
                {OPTION_KEYS.map((key) => <label key={key}><span>选项 {key}</span><input value={editor.options[key]} onChange={(e) => setEditor({ ...editor, options: { ...editor.options, [key]: e.target.value } })} /></label>)}
              </div>
              <div className="field-grid">
                <label><span>大类</span><input list="category-options" value={editor.category} onChange={(e) => setEditor({ ...editor, category: e.target.value })} /><datalist id="category-options">{categories.map((category) => <option key={category} value={category} />)}</datalist></label>
                <label><span>章节</span><input list="section-options" value={editor.section} onChange={(e) => setEditor({ ...editor, section: e.target.value })} /><datalist id="section-options">{sections.map((section) => <option key={section} value={section} />)}</datalist></label>
              </div>
              <div className="field-grid">
                <label><span>正确答案 <em>*</em></span><input value={editor.answer} onChange={(e) => setEditor({ ...editor, answer: e.target.value.toUpperCase() })} placeholder="例如 A 或 A,B" required /></label>
                <label><span>难度</span><select value={editor.difficulty} onChange={(e) => setEditor({ ...editor, difficulty: e.target.value as Difficulty })}><option>基础</option><option>进阶</option><option>困难</option></select></label>
              </div>
              <label><span>简析</span><textarea rows={3} value={editor.explanation} onChange={(e) => setEditor({ ...editor, explanation: e.target.value })} placeholder="简短说明判断依据" /></label>
              <label><span>试题详解</span><textarea rows={5} value={editor.detailedExplanation} onChange={(e) => setEditor({ ...editor, detailedExplanation: e.target.value })} placeholder="完整说明考点和解题思路" /></label>
              <label><span>标签</span><input value={editor.tags.join("、")} onChange={(e) => setEditor({ ...editor, tags: e.target.value.split(/[,，、]/).map((tag) => tag.trim()).filter(Boolean) })} placeholder="多个标签用顿号分隔" /></label>
              <label><span>发布状态</span><select value={editor.status} onChange={(e) => setEditor({ ...editor, status: e.target.value as Status })}><option>草稿</option><option>待审核</option><option>已发布</option></select></label>
              <div className="drawer-actions">{!isNew && <button type="button" className="danger" onClick={deleteQuestion}>删除</button>}<span /><button type="button" className="ghost" onClick={() => setEditor(null)}>取消</button><button className="primary" type="submit">保存题目</button></div>
            </form>
          </aside>
        </div>
      )}

      {quiz.length > 0 && (
        <div className="modal-backdrop">
          <section className="quiz-modal">
            <div className="drawer-head"><div><p>QUIZ PREVIEW</p><h2>随机试卷预览</h2></div><button onClick={() => setQuiz([])} aria-label="关闭">×</button></div>
            <p className="quiz-summary">已从当前筛选范围随机抽取 {quiz.length} 道已发布题目。</p>
            <ol>{quiz.map((item) => <li key={item.id}><span>{item.section} · {item.type}</span><strong>{item.title}</strong>{item.image && <img className="quiz-image" src={item.image} alt="题图" />}
              <div className="quiz-options">{OPTION_KEYS.filter((key) => item.options[key]).map((key) => <p key={key}><b>{key}</b>{item.options[key]}</p>)}</div>
              <details><summary>查看答案与解析</summary><p><strong>{answerText(item)}</strong><br />{item.explanation}<br />{item.detailedExplanation}</p></details></li>)}</ol>
            <button className="primary wide" onClick={() => window.print()}>打印 / 导出 PDF</button>
          </section>
        </div>
      )}

      {zoomImage && <div className="image-lightbox" onClick={() => setZoomImage("")}><button aria-label="关闭原图">×</button><img src={zoomImage} alt="题目原图" /></div>}

      <input ref={fileInput} type="file" accept="application/json,.json" hidden onChange={importJson} />
      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}
