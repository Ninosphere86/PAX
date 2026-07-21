"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";

type QuestionType = "单选题" | "多选题" | "判断题" | "简答题";
type Difficulty = "基础" | "进阶" | "困难";
type Status = "已发布" | "待审核" | "草稿";

type Question = {
  id: string;
  code: string;
  title: string;
  type: QuestionType;
  category: string;
  difficulty: Difficulty;
  answer: string;
  explanation: string;
  tags: string[];
  status: Status;
  updatedAt: string;
};

const STORAGE_KEY = "pingan-question-bank-v1";

const seedQuestions: Question[] = [
  {
    id: "q-001",
    code: "AQ-001",
    title: "机动车通过没有交通信号灯的交叉路口时，应当如何通行？",
    type: "单选题",
    category: "道路通行",
    difficulty: "基础",
    answer: "减速慢行，并让行人和优先通行的车辆先行",
    explanation: "通过无信号灯控制的交叉路口应先观察、减速并依法让行。",
    tags: ["交叉路口", "让行"],
    status: "已发布",
    updatedAt: "2026-07-21",
  },
  {
    id: "q-002",
    code: "AQ-002",
    title: "车辆发生故障停在道路上后，驾驶人应采取哪些措施？",
    type: "多选题",
    category: "应急处置",
    difficulty: "进阶",
    answer: "开启危险报警闪光灯；在来车方向设置警告标志；人员转移到安全区域",
    explanation: "优先警示后方来车并保障现场人员安全。",
    tags: ["故障", "应急"],
    status: "已发布",
    updatedAt: "2026-07-20",
  },
  {
    id: "q-003",
    code: "AQ-003",
    title: "在雨天湿滑路面上，紧急制动距离通常会缩短。",
    type: "判断题",
    category: "安全驾驶",
    difficulty: "基础",
    answer: "错误",
    explanation: "湿滑路面附着力降低，制动距离通常会增加。",
    tags: ["雨天", "制动距离"],
    status: "待审核",
    updatedAt: "2026-07-18",
  },
  {
    id: "q-004",
    code: "AQ-004",
    title: "简述长下坡路段应避免长时间连续踩制动踏板的原因。",
    type: "简答题",
    category: "安全驾驶",
    difficulty: "困难",
    answer: "连续制动会导致制动系统过热、效能衰减，应合理使用低速档和发动机制动。",
    explanation: "考查长下坡制动热衰减风险与正确操作。",
    tags: ["长下坡", "制动热衰减"],
    status: "草稿",
    updatedAt: "2026-07-17",
  },
];

const blankQuestion = (): Question => ({
  id: crypto.randomUUID(),
  code: "",
  title: "",
  type: "单选题",
  category: "安全驾驶",
  difficulty: "基础",
  answer: "",
  explanation: "",
  tags: [],
  status: "草稿",
  updatedAt: new Date().toISOString().slice(0, 10),
});

function csvEscape(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

function statusClass(status: Status) {
  return status === "已发布" ? "published" : status === "待审核" ? "review" : "draft";
}

export default function Home() {
  const [questions, setQuestions] = useState<Question[]>(seedQuestions);
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("全部题型");
  const [categoryFilter, setCategoryFilter] = useState("全部分类");
  const [statusFilter, setStatusFilter] = useState("全部状态");
  const [editor, setEditor] = useState<Question | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [toast, setToast] = useState("");
  const [quiz, setQuiz] = useState<Question[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setQuestions(JSON.parse(saved));
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) localStorage.setItem(STORAGE_KEY, JSON.stringify(questions));
  }, [questions, ready]);

  const categories = useMemo(
    () => [...new Set(questions.map((question) => question.category))].sort(),
    [questions],
  );

  const visibleQuestions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return questions.filter((question) => {
      const haystack = [question.code, question.title, question.answer, question.tags.join(" ")]
        .join(" ")
        .toLowerCase();
      return (
        (!needle || haystack.includes(needle)) &&
        (typeFilter === "全部题型" || question.type === typeFilter) &&
        (categoryFilter === "全部分类" || question.category === categoryFilter) &&
        (statusFilter === "全部状态" || question.status === statusFilter)
      );
    });
  }, [questions, query, typeFilter, categoryFilter, statusFilter]);

  const flash = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2200);
  };

  const startNew = () => {
    const item = blankQuestion();
    item.code = `AQ-${String(questions.length + 1).padStart(3, "0")}`;
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
    link.download = `理论题库-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
    flash("题库已导出");
  };

  const exportCsv = () => {
    const headers = ["编号", "题干", "题型", "分类", "难度", "答案", "解析", "标签", "状态"];
    const rows = questions.map((item) =>
      [item.code, item.title, item.type, item.category, item.difficulty, item.answer, item.explanation, item.tags.join("|"), item.status]
        .map(csvEscape)
        .join(","),
    );
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
      const incoming = JSON.parse(await file.text()) as Question[];
      if (!Array.isArray(incoming)) throw new Error();
      const normalized = incoming.map((item, index) => ({
        ...item,
        id: item.id || crypto.randomUUID(),
        code: item.code || `IMP-${String(index + 1).padStart(3, "0")}`,
        tags: Array.isArray(item.tags) ? item.tags : [],
        updatedAt: item.updatedAt || new Date().toISOString().slice(0, 10),
      }));
      setQuestions(normalized);
      flash(`已导入 ${normalized.length} 道题`);
    } catch {
      flash("导入失败：请选择正确的 JSON 题库文件");
    } finally {
      event.target.value = "";
    }
  };

  const buildQuiz = () => {
    const source = visibleQuestions.filter((item) => item.status === "已发布");
    const shuffled = [...source].sort(() => Math.random() - 0.5).slice(0, Math.min(10, source.length));
    setQuiz(shuffled);
    if (!shuffled.length) flash("当前筛选结果中没有已发布题目");
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">平</span>
          <div>
            <strong>平安线题库</strong>
            <small>KNOWLEDGE OPERATIONS</small>
          </div>
        </div>
        <nav aria-label="题库导航">
          <button className="nav-item active"><span>▦</span> 题目管理 <b>{questions.length}</b></button>
          <button className="nav-item" onClick={buildQuiz}><span>◇</span> 随机组卷</button>
          <button className="nav-item" onClick={() => fileInput.current?.click()}><span>⇧</span> 批量导入</button>
          <button className="nav-item" onClick={exportJson}><span>⇩</span> 题库备份</button>
        </nav>
        <div className="category-list">
          <p>分类</p>
          <button className={categoryFilter === "全部分类" ? "selected" : ""} onClick={() => setCategoryFilter("全部分类")}>
            <span>全部题目</span><b>{questions.length}</b>
          </button>
          {categories.map((category) => (
            <button key={category} className={categoryFilter === category ? "selected" : ""} onClick={() => setCategoryFilter(category)}>
              <span>{category}</span><b>{questions.filter((item) => item.category === category).length}</b>
            </button>
          ))}
        </div>
        <div className="sidebar-note">
          <span className="pulse" />
          <div><strong>本地安全保存</strong><small>数据仅保存在当前浏览器</small></div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">理论考核资产中心</p>
            <h1>题目管理</h1>
          </div>
          <div className="top-actions">
            <button className="ghost" onClick={exportCsv}>导出 CSV</button>
            <button className="primary" onClick={startNew}><span>+</span> 新增题目</button>
          </div>
        </header>

        <section className="metrics" aria-label="题库统计">
          <article><span>总题数</span><strong>{questions.length}</strong><small>全部已录入题目</small></article>
          <article><span>已发布</span><strong>{questions.filter((q) => q.status === "已发布").length}</strong><small>可用于组卷</small></article>
          <article><span>待审核</span><strong>{questions.filter((q) => q.status === "待审核").length}</strong><small>需内容复核</small></article>
          <article><span>题目分类</span><strong>{categories.length}</strong><small>覆盖知识领域</small></article>
        </section>

        <section className="content-card">
          <div className="filters">
            <label className="search">
              <span>⌕</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索编号、题干、答案或标签" />
            </label>
            <select aria-label="题型" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              <option>全部题型</option><option>单选题</option><option>多选题</option><option>判断题</option><option>简答题</option>
            </select>
            <select aria-label="状态" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option>全部状态</option><option>已发布</option><option>待审核</option><option>草稿</option>
            </select>
            <button className="icon-button" title="清空筛选" onClick={() => { setQuery(""); setTypeFilter("全部题型"); setCategoryFilter("全部分类"); setStatusFilter("全部状态"); }}>↻</button>
          </div>

          <div className="table-wrap">
            <table>
              <thead><tr><th>编号</th><th>题干</th><th>题型</th><th>分类</th><th>难度</th><th>状态</th><th>更新日期</th><th /></tr></thead>
              <tbody>
                {visibleQuestions.map((question) => (
                  <tr key={question.id} onDoubleClick={() => { setEditor(question); setIsNew(false); }}>
                    <td><code>{question.code}</code></td>
                    <td className="question-cell"><strong>{question.title}</strong><small>{question.tags.map((tag) => `#${tag}`).join("  ")}</small></td>
                    <td><span className="type-pill">{question.type}</span></td>
                    <td>{question.category}</td>
                    <td><span className={`difficulty ${question.difficulty}`}>{question.difficulty}</span></td>
                    <td><span className={`status ${statusClass(question.status)}`}><i />{question.status}</span></td>
                    <td>{question.updatedAt}</td>
                    <td><button className="edit-button" aria-label={`编辑 ${question.code}`} onClick={() => { setEditor(question); setIsNew(false); }}>编辑</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!visibleQuestions.length && <div className="empty"><strong>没有找到匹配题目</strong><span>请调整搜索词或筛选条件</span></div>}
          </div>
          <footer className="table-footer"><span>当前显示 {visibleQuestions.length} / {questions.length} 道题</span><span>双击行可快速编辑</span></footer>
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
              <div className="field-grid">
                <label><span>分类</span><input list="category-options" value={editor.category} onChange={(e) => setEditor({ ...editor, category: e.target.value })} /><datalist id="category-options">{categories.map((category) => <option key={category} value={category} />)}</datalist></label>
                <label><span>难度</span><select value={editor.difficulty} onChange={(e) => setEditor({ ...editor, difficulty: e.target.value as Difficulty })}><option>基础</option><option>进阶</option><option>困难</option></select></label>
              </div>
              <label><span>参考答案 <em>*</em></span><textarea rows={3} value={editor.answer} onChange={(e) => setEditor({ ...editor, answer: e.target.value })} placeholder="输入正确答案或答案要点" required /></label>
              <label><span>答案解析</span><textarea rows={3} value={editor.explanation} onChange={(e) => setEditor({ ...editor, explanation: e.target.value })} placeholder="说明考点和判定依据" /></label>
              <label><span>标签</span><input value={editor.tags.join("、")} onChange={(e) => setEditor({ ...editor, tags: e.target.value.split(/[,，、]/).map((tag) => tag.trim()).filter(Boolean) })} placeholder="多个标签用顿号分隔" /></label>
              <label><span>发布状态</span><select value={editor.status} onChange={(e) => setEditor({ ...editor, status: e.target.value as Status })}><option>草稿</option><option>待审核</option><option>已发布</option></select></label>
              <div className="drawer-actions">
                {!isNew && <button type="button" className="danger" onClick={deleteQuestion}>删除</button>}
                <span />
                <button type="button" className="ghost" onClick={() => setEditor(null)}>取消</button>
                <button className="primary" type="submit">保存题目</button>
              </div>
            </form>
          </aside>
        </div>
      )}

      {quiz.length > 0 && (
        <div className="modal-backdrop">
          <section className="quiz-modal">
            <div className="drawer-head"><div><p>QUIZ PREVIEW</p><h2>随机试卷预览</h2></div><button onClick={() => setQuiz([])} aria-label="关闭">×</button></div>
            <p className="quiz-summary">已从当前筛选范围随机抽取 {quiz.length} 道已发布题目。</p>
            <ol>{quiz.map((item) => <li key={item.id}><span>{item.type} · {item.difficulty}</span><strong>{item.title}</strong><details><summary>查看答案</summary><p>{item.answer}</p></details></li>)}</ol>
            <button className="primary wide" onClick={() => window.print()}>打印 / 导出 PDF</button>
          </section>
        </div>
      )}

      <input ref={fileInput} type="file" accept="application/json,.json" hidden onChange={importJson} />
      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}
