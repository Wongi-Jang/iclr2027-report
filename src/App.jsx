import React, { useMemo, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  ResponsiveContainer, Tooltip, LabelList,
} from 'recharts'
// Each page entry calls init() with its own venue's report before rendering,
// so one component tree serves every venue without a build-time swap.
let meta, topics, risers, fallers, top_papers, rating_distribution, topicTop
let V, MULTIYEAR, ACCEPTED_ONLY, UNIT, PAGES, CITES

export function init(report, pages = []) {
  ({ meta, topics, risers, fallers, top_papers, rating_distribution } = report)
  topicTop = report.topic_top || {}
  YEARS = meta.years
  V = `${meta.venue} ${meta.latest}`
  MULTIYEAR = meta.years.length > 1
  ACCEPTED_ONLY = meta.corpus === 'accepted-only'
  UNIT = ACCEPTED_ONLY ? 'accepted papers' : 'submissions'
  CITES = !!meta.has_citations
  PAGES = pages
}
let YEARS
const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)',
  'var(--series-4)', 'var(--series-5)', 'var(--series-7)']
const MAX_SERIES = SERIES.length
const n = (x) => x.toLocaleString('en-US')
const paper = (id) => `https://openreview.net/forum?id=${id}`

const axis = { stroke: 'var(--text-muted)', fontSize: 12 }
const cites = (v) => (v === null || v === undefined
  ? <span title="no confident match in OpenAlex" style={{ color: 'var(--text-muted)' }}>&mdash;</span>
  : n(v))

function Tip({ active, payload, label, unit = '' }) {
  if (!active || !payload?.length) return null
  return (
    <div className="tt">
      <div className="tl">{label}</div>
      {payload.map((p) => (
        <div className="tr" key={p.name} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString('en-US') : p.value}{unit}
        </div>
      ))}
    </div>
  )
}

function Header() {
  const growth = (y, prev) => prev ? `+${Math.round(100 * (meta.submissions[y] / prev - 1))}% vs ${y - 1}` : ''
  return (
    <header className="top">
      <nav className="venues">
        {PAGES.map((p) => (
          p.current
            ? <strong key={p.href}>{p.name}</strong>
            : <a key={p.href} href={p.href}>{p.name}</a>
        ))}
      </nav>
      <h1>{V} in numbers</h1>
      <p className="sub">
        Every {V} {ACCEPTED_ONLY ? 'accepted paper' : 'submission'}, labelled against{' '}
        {meta.n_concepts} research concepts
        {MULTIYEAR && <>, with {meta.years.length > 2
          ? <>{meta.years[0]}&ndash;{meta.years.at(-2)}</>
          : meta.years[0]} for comparison</>}.
        Built from the public OpenReview record.
      </p>
      <p className="asof">Data as of {meta.as_of}. {meta.corpus_note}</p>
      <div className="tiles">
        {YEARS.map((y, i) => (
          <div className={`tile${y === meta.latest ? ' hero' : ''}`} key={y}>
            <div className="k">{meta.venue} {y}</div>
            <div className="v">{n(meta.submissions[y])}</div>
            <div className="d">{growth(y, meta.submissions[YEARS[i - 1]])}</div>
          </div>
        ))}
      </div>
    </header>
  )
}

// Recharts axis width is a number, not CSS, so track the viewport for it.
function useNarrow() {
  const [narrow, setNarrow] = useState(
    typeof window !== 'undefined' && window.innerWidth < 640)
  React.useEffect(() => {
    const on = () => setNarrow(window.innerWidth < 640)
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  return narrow
}

function TopicBars() {
  const [all, setAll] = useState(false)
  const narrow = useNarrow()
  const shown = all ? topics : topics.slice(0, 35)
  const data = shown.map((t) => ({ label: t.label, papers: t.counts[meta.latest] }))
  return (
    <section>
      <h2>What {V} is working on</h2>
      <p className="note">
        Papers per concept among the {n(meta.labelled[meta.latest])} labelled {meta.latest}{' '}
        {UNIT}. A paper can match more than one concept, so these counts overlap and do not sum
        to the total.
      </p>
      <div className="card">
        <ResponsiveContainer width="100%" height={all ? 1850 : 900}>
          <BarChart data={data} layout="vertical"
            margin={{ left: narrow ? 0 : 8, right: narrow ? 42 : 56, top: 4, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" {...axis} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="label" width={narrow ? 128 : 236} {...axis}
              tickLine={false} axisLine={false} interval={0}
              tickFormatter={(v) => (narrow && v.length > 20 ? v.slice(0, 19) + '\u2026' : v)} />
            <Tooltip content={<Tip />} cursor={{ fill: 'var(--grid)', opacity: 0.45 }} />
            <Bar dataKey="papers" name="Papers" fill="var(--seq-400)" radius={[0, 4, 4, 0]} barSize={all ? 12 : 16}>
              <LabelList dataKey="papers" position="right" fill="var(--text-secondary)" fontSize={11} formatter={n} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details>
        <summary onClick={() => setAll(!all)}>
          {all ? 'Show only the top 35' : `Show all ${topics.length} concepts`}
        </summary>
      </details>
    </section>
  )
}

const DEFAULTS = ['llm-agents', 'world-models', 'agent-memory', 'diffusion-lm', 'mech-interp', 'jepa']

function Trend() {
  const [picked, setPicked] = useState(
    DEFAULTS.filter((id) => topics.some((t) => t.id === id)).slice(0, MAX_SERIES))
  const [table, setTable] = useState(false)
  const byId = useMemo(() => Object.fromEntries(topics.map((t) => [t.id, t])), [])
  const data = YEARS.map((y) => {
    const row = { year: String(y) }
    picked.forEach((id) => { row[byId[id].label] = byId[id].share[y] })
    return row
  })
  const toggle = (id) => setPicked((cur) =>
    cur.includes(id) ? cur.filter((x) => x !== id)
      : cur.length >= MAX_SERIES ? cur : [...cur, id])

  return (
    <section>
      <h2>{meta.years.length} years of concept share</h2>
      <p className="note">
        Share of each year&rsquo;s labelled {UNIT} that work on a concept. Share, not raw count,
        because the conference grew steeply over this period &mdash; almost everything rises in
        absolute terms. Pick up to {MAX_SERIES} concepts.
      </p>
      <div className="controls">
        {[...topics.slice(0, 28), ...topics.filter(
          (t) => picked.includes(t.id) && !topics.slice(0, 28).includes(t))].map((t) => {
          const on = picked.includes(t.id)
          return (
            <button className="chip" key={t.id} aria-pressed={on} onClick={() => toggle(t.id)}
              style={on ? { color: SERIES[picked.indexOf(t.id) % MAX_SERIES] } : undefined}>
              {on && <span className="dot" style={{ background: SERIES[picked.indexOf(t.id) % MAX_SERIES] }} />}
              {t.label}
            </button>
          )
        })}
      </div>
      <div className="card">
        <ResponsiveContainer width="100%" height={420}>
          <LineChart data={data} margin={{ left: 4, right: 16, top: 10, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" {...axis} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
            <YAxis {...axis} tickLine={false} axisLine={false} unit="%" />
            <Tooltip content={<Tip unit="%" />} />
            {picked.map((id, i) => (
              <Line key={id} type="monotone" dataKey={byId[id].label} stroke={SERIES[i % MAX_SERIES]}
                strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: 'var(--surface-1)' }} activeDot={{ r: 6 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details open={table}>
        <summary onClick={(e) => { e.preventDefault(); setTable(!table) }}>
          {table ? 'Hide' : 'Show'} the numbers as a table
        </summary>
        {table && (
          <table>
            <thead><tr><th>Concept</th>{YEARS.map((y) => <th className="num" key={y}>{y}</th>)}</tr></thead>
            <tbody>
              {picked.map((id) => (
                <tr key={id}>
                  <td>{byId[id].label}</td>
                  {YEARS.map((y) => (
                    <td className="num" key={y}>{byId[id].share[y]}% <span style={{ color: 'var(--text-muted)' }}>({n(byId[id].counts[y])})</span></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </section>
  )
}

function Movers() {
  const t = (rows, caption) => (
    <div>
      <h2 style={{ fontSize: 17 }}>{caption}</h2>
      <table>
        <thead><tr><th>Concept</th><th className="num">{meta.years.at(-2)}</th>
          <th className="num">{meta.latest}</th><th className="num">Change</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.label}<div className="chips"><span>{n(r.n2027)} papers</span></div></td>
              <td className="num">{r.from}%</td>
              <td className="num">{r.to}%</td>
              <td className="num" style={{ color: r.delta > 0 ? 'var(--series-3)' : 'var(--series-2)' }}>
                {r.delta > 0 ? '+' : ''}{r.delta} pts
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
  return (
    <section>
      <h2>Risers and fallers</h2>
      <p className="note">
        Change in share of {UNIT} from {meta.venue} {meta.years.at(-2)} to {V}, in percentage points.
        Concepts with fewer than 50 papers across both years are left out as too noisy.
      </p>
      <div className="two">{t(risers, 'Rising')}{t(fallers, 'Falling')}</div>
    </section>
  )
}

function Ratings() {
  const data = Object.entries(rating_distribution).map(([k, v]) => ({ rating: k, reviews: v }))
  return (
    <section>
      <h2>How {V} is scoring papers</h2>
      <p className="note">
        {Object.keys(meta.rating_scales).length > 0
          ? <>Rating scales differ by year ({Object.entries(meta.rating_scales)
              .map(([y, s]) => `${y}: ${s}`).join(', ')}), so scores are never compared across
              years in this report.</>
          : <>Distribution of individual reviewer ratings for {V}.</>}
      </p>
      <div className="card">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ left: 4, right: 12, top: 14, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="rating" {...axis} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
            <YAxis {...axis} tickLine={false} axisLine={false} />
            <Tooltip content={<Tip />} cursor={{ fill: 'var(--grid)', opacity: 0.45 }} />
            <Bar dataKey="reviews" name="Reviews" fill="var(--seq-400)" radius={[4, 4, 0, 0]} maxBarSize={110}>
              <LabelList dataKey="reviews" position="top" fill="var(--text-secondary)" fontSize={11} formatter={n} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function PaperTable({ rows, caption, note }) {
  return (
    <section>
      <h2>{caption}</h2>
      <p className="note">{note}</p>
      <table>
        <thead>
          <tr>
            <th className="num">#</th><th>Paper</th>
            <th className="num">Mean</th><th className="num">Reviews</th>
            {CITES && <th className="num">Citations</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id}>
              <td className="num" style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
              <td>
                <a href={paper(r.id)} target="_blank" rel="noreferrer">{r.title}</a>
                {r.topics.length > 0 && <div className="chips">{r.topics.map((t) => <span key={t}>{t}</span>)}</div>}
              </td>
              <td className="num">{r.mean.toFixed(2)}</td>
              <td className="num">{r.n}</td>
              {CITES && <td className="num">{cites(r.cites)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function TopicLeaderboard() {
  const ids = Object.keys(topicTop)
  const [pick, setPick] = useState(ids[0])
  if (ids.length === 0) return null
  const sel = topicTop[pick]
  return (
    <section>
      <h2>Best-rated work by concept</h2>
      <p className="note">
        The highest-rated {meta.latest} papers within one concept, among papers with at least
        three reviews. Useful for &ldquo;what is the strongest work on world models&rdquo; rather
        than only &ldquo;what scored highest overall&rdquo;. Ratings are coarse, so ties are
        common and the order within a tie is by review count, not by merit.
      </p>
      <div className="controls">
        <label className="pickrow">
          <span>Concept</span>
          <select value={pick} onChange={(e) => setPick(e.target.value)}>
            {ids.map((id) => (
              <option key={id} value={id}>
                {topicTop[id].label} ({n(topicTop[id].n_rated)})
              </option>
            ))}
          </select>
        </label>
      </div>
      <table>
        <thead>
          <tr><th className="num">#</th><th>Paper</th><th className="num">Mean</th>
            <th className="num">Reviews</th>{CITES && <th className="num">Citations</th>}</tr>
        </thead>
        <tbody>
          {sel.papers.map((r, i) => (
            <tr key={r.id}>
              <td className="num" style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
              <td><a href={paper(r.id)} target="_blank" rel="noreferrer">{r.title}</a></td>
              <td className="num">{r.mean.toFixed(2)}</td>
              <td className="num">{r.n}</td>
              {CITES && <td className="num">{cites(r.cites)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note" style={{ marginTop: 10 }}>
        {n(sel.n_rated)} rated {meta.latest} papers carry this concept.
      </p>
    </section>
  )
}

function Method() {
  return (
    <section>
      <h2>Method and caveats</h2>
      <p className="note">Read this before quoting any number above.</p>
      <table>
        <tbody>
          <tr><th style={{ width: 190 }}>Source</th><td>The public OpenReview record for {meta.venue} {meta.years[0]}&ndash;{meta.latest}, fetched {meta.as_of} via the authenticated API.</td></tr>
          <tr><th>What the corpus is</th><td>{meta.corpus_note}</td></tr>
          <tr><th>What counts</th><td>{meta.excluded_note} Analysed: {YEARS.map((y) => `${y}: ${n(meta.analysed[y])}`).join(', ')}.</td></tr>
          <tr><th>Concept labels</th><td>Each paper&rsquo;s title, keywords and abstract were labelled against {meta.n_concepts} hand-curated concepts by Claude Haiku 5.5. The exact list used is <code>{meta.taxonomy_file}</code> in the repository.</td></tr>
          {Object.entries(meta.caveats || {}).map(([k, v]) => (
            <tr key={k}><th>{k}</th><td>{v}</td></tr>
          ))}
          <tr><th>Overlap</th><td>Concepts are not mutually exclusive. A paper may carry up to three, so concept counts overlap and shares do not sum to 100%.</td></tr>
          {Object.keys(meta.rating_scales).length > 0 && (
            <tr><th>Rating scales</th><td>{Object.entries(meta.rating_scales)
              .map(([y, sc]) => `${y}: ${sc}`).join(', ')}. Never compared across years.</td></tr>
          )}
          {CITES && <tr><th>Citations</th><td>From OpenAlex, matched by exact title. A paper whose
            title does not match confidently shows &mdash; rather than a number, because a near-miss
            would attribute another paper&rsquo;s citations to it. Counts move over time; they were
            fetched on {meta.as_of}.</td></tr>}
          <tr><th>Authors</th><td>Where a venue withholds author names during review, the tables above show titles without authors.</td></tr>
        </tbody>
      </table>
    </section>
  )
}

export default function App() {
  return (
    <div className="wrap">
      <Header />
      <TopicBars />
      {MULTIYEAR && <Trend />}
      {MULTIYEAR && <Movers />}
      <Ratings />
      <PaperTable rows={top_papers} caption={`Highest-rated ${UNIT}`}
        note={`Top ${top_papers.length} of the labelled ${meta.latest} ${UNIT} by mean reviewer`
          + ` rating, among papers with at least three reviews.`
          + (meta.rating_scales[meta.latest] ? ` On a ${meta.rating_scales[meta.latest]} scale ties`
             + ` are common; order within a tie is by review count.` : '')
          + (ACCEPTED_ONLY ? '' : ' A high score here is not an acceptance - no decisions have been released.')} />
      <TopicLeaderboard />
      <Method />
      <footer>
        Built from public OpenReview data. Not affiliated with {meta.venue} or OpenReview.
        Pipeline and concept list: <a href="https://github.com/Wongi-Jang/ml-conference-reports">github.com/Wongi-Jang/ml-conference-reports</a>.
      </footer>
    </div>
  )
}
