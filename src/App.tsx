import { useEffect, useMemo, useState } from 'react'
import {
  CHAPTERS,
  KIND_LABEL,
  SOURCE_LABEL,
  type Chapter,
  type Question,
  type QuestionKind,
  type SourceId,
} from './types'
import { QUESTIONS } from './data'
import { generatePyqMcqs, mcqDtoToQuestion } from './api/pyqMcq'
import {
  fetchPyqApiHealth,
  fetchPyqSpread,
  generatePyqPaperStream,
  PAPER_MARKS_OPTIONS,
} from './api/pyqPaper'
import { ChemistryText } from './components/ChemistryText'
import type { PyqReference } from './types'
import { downloadPaperHtml, downloadPaperMarkdown } from './exportPaper'
import {
  bankStats,
  cbseSpreadForTotal,
  formatSectionSpread,
  generatePaper,
  marksFromSectionCounts,
  type GeneratedPaper,
} from './generator'

const ALL_SOURCES = Object.keys(SOURCE_LABEL) as SourceId[]

function PyqAttribution({
  pyqRef,
  compact = false,
}: {
  pyqRef: PyqReference
  compact?: boolean
}) {
  if (compact) {
    return (
      <div className="pyq-ref">
        <strong>Based on board PYQ:</strong> {pyqRef.label}
      </div>
    )
  }
  return (
    <div className="pyq-ref">
      <strong>Based on board PYQ:</strong> {pyqRef.label}
      <div className="pyq-ref-detail">
        Original question: <ChemistryText text={pyqRef.stem} />
        {pyqRef.markingAnswer ? (
          <>
            <br />
            Marking scheme (1-line): <ChemistryText text={pyqRef.markingAnswer} />
          </>
        ) : null}
      </div>
      <div className="pyq-ref-note">
        {pyqRef.generationStyle === 'creative'
          ? 'New question below is inspired by this PYQ (creative mode).'
          : 'Same board question below; only the four options are generated (strict mode).'}
      </div>
    </div>
  )
}

function QuestionBody({
  q,
  showAnswer,
  inPaper = false,
}: {
  q: Question
  showAnswer: boolean
  inPaper?: boolean
}) {
  return (
    <div>
      {!inPaper ? (
        <div className="meta">
          <span className="pill">{q.chapter}</span>
          <span className="pill">{KIND_LABEL[q.kind]}</span>
          <span className="pill">{SOURCE_LABEL[q.source]}</span>
          <span className="pill">{q.marks} mark{q.marks > 1 ? 's' : ''}</span>
        </div>
      ) : null}
      {q.pyqReference ? (
        <PyqAttribution pyqRef={q.pyqReference} compact={inPaper} />
      ) : null}
      {q.figureNote ? <p className="figure-note">{q.figureNote}</p> : null}
      <ChemistryText text={q.text} />
      {q.options ? (
        <ol className="options" type="a">
          {q.options.map((opt) => (
            <li key={opt}><ChemistryText text={opt} /></li>
          ))}
        </ol>
      ) : null}
      {q.orText ? (
        <div className="or">
          <strong>OR</strong>
          <div style={{ whiteSpace: 'pre-wrap', marginTop: 4 }}>{q.orText}</div>
        </div>
      ) : null}
      {showAnswer && q.answer ? (
        <div className="answer">Answer / key: <ChemistryText text={q.answer} /></div>
      ) : null}
    </div>
  )
}

function PaperView({ paper, showAnswers }: { paper: GeneratedPaper; showAnswers: boolean }) {
  return (
    <article className="paper">
      <header className="paper-head">
        <h2>{paper.title}</h2>
        <div>{paper.subtitle}</div>
        <div className="paper-meta">
          <span>Time allowed: {paper.time}</span>
          <span>
            Maximum marks: {paper.maxMarks}
            {paper.targetMarks !== paper.maxMarks
              ? ` (target ${paper.targetMarks})`
              : ` / ${paper.targetMarks}`}
          </span>
          <span className="pill">{paper.sectionSpread}</span>
        </div>
      </header>
      {paper.warnings?.length ? (
        <div className="instructions" style={{ borderColor: '#c9a227' }}>
          <strong>Generation notes</strong>
          <ul>
            {paper.warnings.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="instructions">
        <strong>General instructions</strong>
        <ol>
          {paper.generalInstructions.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      </div>
      {paper.sections.map((section) => (
        <section key={section.title}>
          <h3 className="section-title">{section.title}</h3>
          <p>{section.instruction}</p>
          {section.items.map((item) => (
            <div className="q-block" key={item.number}>
              <div className="q-top">
                <span>Q.{item.number}</span>
                <span className="marks">[{item.marks}]</span>
              </div>
              {item.passage ? <div className="passage">{item.passage}</div> : null}
              {item.figureNote ? <p className="figure-note">{item.figureNote}</p> : null}
              {item.questions.map((q, idx) => (
                <div key={q.id} style={{ marginTop: item.questions.length > 1 ? 10 : 6 }}>
                  {item.questions.length > 1 ? <strong>({idx + 1}) </strong> : null}
                  <QuestionBody q={q} showAnswer={showAnswers} inPaper />
                </div>
              ))}
            </div>
          ))}
        </section>
      ))}
      <p style={{ marginTop: 24, fontSize: 13, color: '#4a433a' }}>
        Paper seed {paper.seed} · generated {new Date(paper.generatedAt).toLocaleString()}
      </p>
    </article>
  )
}

export default function App() {
  const [tab, setTab] = useState<'generate' | 'bank' | 'paper' | 'pyq'>('generate')
  const [pyqMcqs, setPyqMcqs] = useState<Question[]>([])
  const [pyqLoading, setPyqLoading] = useState(false)
  const [pyqError, setPyqError] = useState<string | null>(null)
  const [pyqChapter, setPyqChapter] = useState<Chapter>(CHAPTERS[0])
  const [pyqCount, setPyqCount] = useState(8)
  const [pyqAiLevel, setPyqAiLevel] = useState(0)
  const [pyqPaperMarks, setPyqPaperMarks] = useState(70)
  const [pyqPaperChapters, setPyqPaperChapters] = useState<Chapter[]>([...CHAPTERS])
  const [pyqPaperLoading, setPyqPaperLoading] = useState(false)
  const [pyqPaperProgress, setPyqPaperProgress] = useState<{
    step: number
    total: number
    message: string
  } | null>(null)
  const [pyqPaperApiReady, setPyqPaperApiReady] = useState<boolean | null>(null)
  useEffect(() => {
    if (tab !== 'pyq') return
    void fetchPyqApiHealth().then((h) => {
      setPyqPaperApiReady(h ? h.paperApi : false)
    })
  }, [tab])
  const [pyqSpreadPreview, setPyqSpreadPreview] = useState({
    label: formatSectionSpread(cbseSpreadForTotal(70)),
    total: 70,
    corpusNote: null as string | null,
  })
  useEffect(() => {
    if (tab !== 'pyq') return
    const ch = pyqPaperChapters.length ? pyqPaperChapters : undefined
    void fetchPyqSpread(pyqPaperMarks, ch).then((s) => {
      if (s) {
        setPyqSpreadPreview({
          label: s.spread,
          total: s.targetMarks,
          corpusNote:
            s.corpusNotes?.[0] ??
            (s.plannedSpread && s.plannedSpread !== s.spread
              ? `CBSE template was ${s.plannedSpread}; adjusted for your corpus.`
              : null),
        })
      } else {
        const c = cbseSpreadForTotal(pyqPaperMarks)
        setPyqSpreadPreview({
          label: formatSectionSpread(c),
          total: marksFromSectionCounts(c),
          corpusNote: null,
        })
      }
    })
  }, [tab, pyqPaperMarks, pyqPaperChapters])
  const [chapters, setChapters] = useState<Chapter[]>([...CHAPTERS])
  const [sources, setSources] = useState<SourceId[]>([...ALL_SOURCES])
  const [paperMarks, setPaperMarks] = useState(70)
  const spreadPreview = useMemo(() => {
    const c = cbseSpreadForTotal(paperMarks)
    return { label: formatSectionSpread(c), total: marksFromSectionCounts(c) }
  }, [paperMarks])
  const [includeAnswers, setIncludeAnswers] = useState(false)
  const [paper, setPaper] = useState<GeneratedPaper | null>(null)
  const [query, setQuery] = useState('')
  const [kindFilter, setKindFilter] = useState<'all' | QuestionKind>('all')
  const [chapterFilter, setChapterFilter] = useState<'all' | Chapter>('all')

  const stats = useMemo(() => bankStats(chapters, sources, pyqMcqs), [chapters, sources, pyqMcqs])

  const bankPool = useMemo(() => [...QUESTIONS, ...pyqMcqs], [pyqMcqs])

  const filteredBank = useMemo(() => {
    const q = query.trim().toLowerCase()
    return bankPool.filter((item) => {
      if (chapterFilter !== 'all' && item.chapter !== chapterFilter) return false
      if (kindFilter !== 'all' && item.kind !== kindFilter) return false
      if (!q) return true
      return (
        item.text.toLowerCase().includes(q) ||
        (item.passage?.toLowerCase().includes(q) ?? false) ||
        item.chapter.toLowerCase().includes(q)
      )
    })
  }, [query, kindFilter, chapterFilter, bankPool])

  function toggleChapter(ch: Chapter) {
    setChapters((prev) => (prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]))
  }
  function toggleSource(id: SourceId) {
    setSources((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]))
  }

  function onGenerate() {
    if (!chapters.length || !sources.length) return
    const paperSources =
      pyqMcqs.length && !sources.includes('pyq')
        ? ([...sources, 'pyq'] as SourceId[])
        : sources
    const next = generatePaper({
      chapters,
      sources: paperSources,
      seed: Date.now() % 1_000_000_007,
      targetMarks: paperMarks,
      extraQuestions: pyqMcqs.length ? pyqMcqs : [],
    })
    setPaper(next)
    setTab('paper')
  }

  return (
    <>
      <header className="app-header">
        <div>
          <h1 className="brand">ChemCompass</h1>
          <p className="tagline">
            Mix official CBSE Class 12 Chemistry questions into a printable practice paper — from
            the Class XII question bank and additional practice papers.
          </p>
        </div>
        <nav className="nav">
          <button className={tab === 'generate' ? 'active' : ''} onClick={() => setTab('generate')}>
            Generate
          </button>
          <button className={tab === 'bank' ? 'active' : ''} onClick={() => setTab('bank')}>
            Question bank
          </button>
          <button className={tab === 'paper' ? 'active' : ''} onClick={() => setTab('paper')}>
            Paper
          </button>
          <button className={tab === 'pyq' ? 'active' : ''} onClick={() => setTab('pyq')}>
            PYQ MCQs
          </button>
        </nav>
      </header>

      <main>
        {tab === 'generate' && (
          <div className="grid-2">
            <div className="panel">
              <fieldset>
                <legend>Marks</legend>
                <label className="field">
                  Total marks (CBSE-style spread)
                  <select
                    value={paperMarks}
                    onChange={(e) => setPaperMarks(Number(e.target.value))}
                  >
                    {PAPER_MARKS_OPTIONS.map((m) => (
                      <option key={m} value={m}>
                        {m} marks
                      </option>
                    ))}
                  </select>
                </label>
                <p className="note" style={{ marginTop: 8 }}>
                  Section mix: <strong>{spreadPreview.label}</strong> = {spreadPreview.total}{' '}
                  marks
                  {paperMarks === 70 ? ' (official CBSE board pattern)' : ''}.
                </p>
              </fieldset>

              <fieldset>
                <legend>Chapters</legend>
                <div className="chips">
                  {CHAPTERS.map((ch) => (
                    <label key={ch}>
                      <input
                        type="checkbox"
                        checked={chapters.includes(ch)}
                        onChange={() => toggleChapter(ch)}
                      />
                      {ch}
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset>
                <legend>Sources</legend>
                <div className="chips">
                  {ALL_SOURCES.map((id) => (
                    <label key={id}>
                      <input
                        type="checkbox"
                        checked={sources.includes(id)}
                        onChange={() => toggleSource(id)}
                      />
                      {SOURCE_LABEL[id]}
                    </label>
                  ))}
                </div>
              </fieldset>

              <label className="check">
                <input
                  type="checkbox"
                  checked={includeAnswers}
                  onChange={(e) => setIncludeAnswers(e.target.checked)}
                />
                Print with answer key
              </label>

              <div className="actions">
                <button className="btn primary" onClick={onGenerate}>
                  Generate paper
                </button>
                <button
                  className="btn ghost"
                  onClick={() => {
                    setChapters([...CHAPTERS])
                    setSources([...ALL_SOURCES])
                  }}
                >
                  Reset filters
                </button>
              </div>
              <p className="note">
                <strong>Section A (1 mark):</strong> MCQs from selected sources (including PYQ MCQs
                if enabled). <strong>Sections B–E (2–5 marks):</strong> short/long answers are always
                drawn from the CBSE question bank &amp; APQ sets for your chapters, even when only
                PYQ is selected for MCQs.
              </p>
            </div>

            <div className="panel">
              <h2 style={{ marginTop: 0 }}>Pool for this mix</h2>
              <div className="stats">
                <div className="stat">
                  <b>{stats.total}</b>
                  <span>questions available</span>
                </div>
                <div className="stat">
                  <b>{Object.keys(stats.byChapter).length}</b>
                  <span>chapters selected</span>
                </div>
              </div>
              <p style={{ marginTop: 12, fontSize: 14 }}>
                <strong>1-mark pool:</strong>{' '}
                {Object.entries(stats.byMarksOneMark ?? {})
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([m, c]) => `${m} mark: ${c}`)
                  .join(' · ') || '—'}
              </p>
              <p style={{ fontSize: 14 }}>
                <strong>2–5 mark bank (for paper):</strong> {stats.subjectiveTotal ?? 0} items (
                {Object.entries(stats.byMarksSubjective ?? {})
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([m, c]) => `${m}m: ${c}`)
                  .join(', ') || '—'}
                )
              </p>
              <ul>
                {Object.entries(stats.byKind).map(([kind, count]) => (
                  <li key={kind}>
                    {KIND_LABEL[kind as QuestionKind] ?? kind}: {count}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {tab === 'pyq' && (
          <div className="panel">
            <h2 style={{ marginTop: 0 }}>Previous year papers (PYQ)</h2>
            {pyqPaperApiReady === false ? (
              <p className="note" style={{ color: '#8b2e2e' }}>
                Paper API not available (404). Stop the old server on port <strong>8787</strong>,
                then start the updated API:{' '}
                <code>cd scripts\pyq-llm</code>,{' '}
                <code>$env:PYTHONPATH=&quot;.&quot;</code>,{' '}
                <code>py -m pyq_llm.main</code>.
              </p>
            ) : null}
            <fieldset>
              <legend>Full PYQ paper</legend>
              <p className="note">
                Builds a paper for your target marks using the CBSE spread. Use the slider to choose
                how much is AI-generated from PYQ topics versus taken from your corpus.
              </p>
              <div className="row">
                <label className="field">
                  Marks
                  <select
                    value={pyqPaperMarks}
                    onChange={(e) => setPyqPaperMarks(Number(e.target.value))}
                  >
                    {PAPER_MARKS_OPTIONS.map((m) => (
                      <option key={m} value={m}>{m} marks</option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="field" style={{ display: 'block', marginTop: 12 }}>
                AI-generated questions: <strong>{pyqAiLevel}%</strong>
                <input
                  type="range"
                  className="ai-blend-slider"
                  min={0}
                  max={100}
                  step={5}
                  value={pyqAiLevel}
                  onChange={(e) => setPyqAiLevel(Number(e.target.value))}
                />
              </label>
              <p className="note" style={{ fontSize: 13 }}>
                Left: corpus PYQs first, AI only fills gaps. Right: all questions AI-generated from
                PYQ topics (slower on local Ollama).
              </p>
              <p className="note" style={{ marginTop: 8 }}>
                Spread: <strong>{pyqSpreadPreview.label}</strong> ({pyqSpreadPreview.total} marks)
                {pyqSpreadPreview.corpusNote ? (
                  <>
                    <br />
                    <span style={{ fontSize: 13 }}>{pyqSpreadPreview.corpusNote}</span>
                  </>
                ) : null}
              </p>
              <p className="note" style={{ fontSize: 13 }}>
                Section A needs {pyqSpreadPreview.label.split('+')[0]?.trim() ?? 'several'} LLM
                MCQs — allow several minutes on local Ollama for a 30-mark paper.
              </p>
              <fieldset style={{ marginTop: 12 }}>
                <legend>Chapters</legend>
                <div className="chips">
                  {CHAPTERS.map((ch) => (
                    <label key={ch}>
                      <input
                        type="checkbox"
                        checked={pyqPaperChapters.includes(ch)}
                        onChange={() =>
                          setPyqPaperChapters((prev) =>
                            prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch],
                          )
                        }
                      />
                      {ch}
                    </label>
                  ))}
                </div>
              </fieldset>
              {pyqPaperProgress ? (
                <div className="paper-progress" style={{ marginTop: 12 }}>
                  <progress
                    value={pyqPaperProgress.step}
                    max={pyqPaperProgress.total}
                  />
                  <p className="note" style={{ margin: '6px 0 0' }}>
                    {pyqPaperProgress.message} ({pyqPaperProgress.step}/
                    {pyqPaperProgress.total})
                  </p>
                </div>
              ) : null}
              <div className="actions" style={{ marginTop: 12 }}>
                <button
                  className="btn primary"
                  disabled={pyqPaperLoading || !pyqPaperChapters.length}
                  onClick={async () => {
                    setPyqError(null)
                    setPyqPaperLoading(true)
                    setPyqPaperProgress(null)
                    try {
                      const next = await generatePyqPaperStream(
                        {
                          chapters: pyqPaperChapters,
                          targetMarks: pyqPaperMarks,
                          aiLevel: pyqAiLevel,
                        },
                        (p) => setPyqPaperProgress(p),
                      )
                      setPaper(next)
                      setTab('paper')
                    } catch (e) {
                      setPyqError(e instanceof Error ? e.message : String(e))
                    } finally {
                      setPyqPaperLoading(false)
                      setPyqPaperProgress(null)
                    }
                  }}
                >
                  {pyqPaperLoading ? 'Building paper…' : 'Generate PYQ paper'}
                </button>
              </div>
            </fieldset>

            <h3>MCQs only (add to Generate tab pool)</h3>
            <p className="note">
              Retrieves similar PYQs and asks an LLM to write four NCERT-style options (no “None of
              these”). Configure an LLM in <code>scripts/pyq-llm/.env</code> — local{' '}
              <strong>Ollama</strong> (<code>USE_OLLAMA=1</code>), free{' '}
              <code>GEMINI_API_KEY</code>, or paid OpenAI — then restart{' '}
              <code>py -m pyq_llm.main</code>.
            </p>
            <div className="row">
              <label className="field">
                Chapter
                <select
                  value={pyqChapter}
                  onChange={(e) => setPyqChapter(e.target.value as Chapter)}
                >
                  {CHAPTERS.map((ch) => (
                    <option key={ch} value={ch}>{ch}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Count
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={pyqCount}
                  onChange={(e) => setPyqCount(Number(e.target.value))}
                />
              </label>
            </div>
            <div className="actions">
              <button
                className="btn primary"
                disabled={pyqLoading}
                onClick={async () => {
                  setPyqError(null)
                  setPyqLoading(true)
                  try {
                    const dtos = await generatePyqMcqs({
                      chapter: pyqChapter,
                      count: pyqCount,
                      stemMode: 'mix',
                    })
                    const qs = dtos.map((d) => mcqDtoToQuestion(d, pyqChapter))
                    setPyqMcqs((prev) => [...prev, ...qs])
                    if (!sources.includes('pyq')) {
                      setSources((s) => [...s, 'pyq'])
                    }
                  } catch (e) {
                    setPyqError(e instanceof Error ? e.message : String(e))
                  } finally {
                    setPyqLoading(false)
                  }
                }}
              >
                {pyqLoading ? 'Generating…' : 'Generate MCQs'}
              </button>
              <button className="btn ghost" onClick={() => setPyqMcqs([])}>
                Clear generated
              </button>
            </div>
            {pyqError ? (
              <p className="note" style={{ color: '#8b2e2e' }}>{pyqError}</p>
            ) : null}
            {(pyqPaperLoading || pyqLoading) && (
              <p className="note">Local LLM: ~1 min per 1-mark MCQ in a full paper.</p>
            )}
            <p className="pill">{pyqMcqs.length} PYQ MCQs in pool</p>
            <div className="q-list">
              {pyqMcqs.slice(-10).map((q) => (
                <article className="q-card" key={q.id}>
                  <QuestionBody q={q} showAnswer />
                </article>
              ))}
            </div>
          </div>
        )}

        {tab === 'bank' && (
          <div className="panel">
            <input
              className="search"
              placeholder="Search questions, passages, chapters…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="filters">
              <select
                value={chapterFilter}
                onChange={(e) => setChapterFilter(e.target.value as Chapter | 'all')}
              >
                <option value="all">All chapters</option>
                {CHAPTERS.map((ch) => (
                  <option key={ch} value={ch}>
                    {ch}
                  </option>
                ))}
              </select>
              <select
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value as QuestionKind | 'all')}
              >
                <option value="all">All types</option>
                {(Object.keys(KIND_LABEL) as QuestionKind[]).map((k) => (
                  <option key={k} value={k}>
                    {KIND_LABEL[k]}
                  </option>
                ))}
              </select>
              <span className="pill">{filteredBank.length} shown</span>
            </div>
            <div className="q-list">
              {filteredBank.map((q) => (
                <article className="q-card" key={q.id}>
                  {q.passage ? <div className="passage">{q.passage}</div> : null}
                  <QuestionBody q={q} showAnswer />
                </article>
              ))}
            </div>
          </div>
        )}

        {tab === 'paper' && (
          <div>
            <div className="toolbar no-print">
              <button className="btn primary" onClick={onGenerate}>
                New combination
              </button>
              <button className="btn warm" onClick={() => window.print()}>
                Print / save PDF
              </button>
              {paper ? (
                <>
                  <button
                    className="btn ghost"
                    onClick={() => downloadPaperHtml(paper, includeAnswers)}
                  >
                    Download HTML
                  </button>
                  <button
                    className="btn ghost"
                    onClick={() => downloadPaperMarkdown(paper, includeAnswers)}
                  >
                    Download Markdown
                  </button>
                </>
              ) : null}
              <button className="btn ghost" onClick={() => setTab('generate')}>
                Edit mix
              </button>
            </div>
            {paper ? (
              <PaperView paper={paper} showAnswers={includeAnswers} />
            ) : (
              <div className="panel">Generate a paper first from the Generate tab.</div>
            )}
          </div>
        )}
      </main>

      <footer className="site">
        Sources: CBSE Academic Question Bank Class XII (
        <a href="https://cbseacademic.nic.in/qbclass12.html">qbclass12.html</a>
        ) and Additional Practice Questions (
        <a href="https://cbseacademic.nic.in/additionalPQ.html">additionalPQ.html</a>
        ). Questions are reproduced for student practice; CBSE remains the copyright holder.
      </footer>
    </>
  )
}
