import React, { useMemo, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  ResponsiveContainer, Tooltip, LabelList,
} from 'recharts'
import report from './data/report.json'

const { meta, topics, risers, fallers, top_papers, contested_papers, rating_distribution } = report
const YEARS = meta.years
const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)',
  'var(--series-4)', 'var(--series-5)', 'var(--series-7)']
const MAX_SERIES = SERIES.length
const n = (x) => x.toLocaleString('en-US')
const paper = (id) => `https://openreview.net/forum?id=${id}`

const axis = { stroke: 'var(--text-muted)', fontSize: 12 }

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
      <h1>ICLR 2027 in numbers</h1>
      <p className="sub">
        Every ICLR 2027 submission, labelled against {meta.n_concepts} research concepts, with
        2024&ndash;2026 for comparison. Built from the public OpenReview record.
      </p>
      <p className="asof">Data as of {meta.as_of}. Reviews are still in progress; no decisions have been released for 2027.</p>
      <div className="tiles">
        {YEARS.map((y, i) => (
          <div className={`tile${y === 2027 ? ' hero' : ''}`} key={y}>
            <div className="k">ICLR {y}</div>
            <div className="v">{n(meta.submissions[y])}</div>
            <div className="d">{growth(y, meta.submissions[YEARS[i - 1]])}</div>
          </div>
        ))}
      </div>
    </header>
  )
}

function TopicBars() {
  const [all, setAll] = useState(false)
  const shown = all ? topics : topics.slice(0, 35)
  const data = shown.map((t) => ({ label: t.label, papers: t.counts[2027] }))
  return (
    <section>
      <h2>What ICLR 2027 is working on</h2>
      <p className="note">
        Papers per concept among the {n(meta.labelled[2027])} labelled 2027 submissions. A paper can
        match more than one concept, so these counts overlap and do not sum to the total.
      </p>
      <div className="card">
        <ResponsiveContainer width="100%" height={all ? 1850 : 900}>
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 56, top: 4, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" horizontal={false} />
            <XAxis type="number" {...axis} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="label" width={236} {...axis} tickLine={false} axisLine={false} interval={0} />
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
      <h2>Four years of concept share</h2>
      <p className="note">
        Share of each year&rsquo;s labelled submissions that work on a concept. Share, not raw
        count, because the conference nearly sextupled over these four years &mdash; almost
        everything grows in absolute terms. Pick up to {MAX_SERIES} concepts.
      </p>
      <div className="controls">
        {topics.slice(0, 28).map((t, i) => {
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
          <LineChart data={data} margin={{ left: 4, right: 128, top: 10, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" {...axis} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
            <YAxis {...axis} tickLine={false} axisLine={false} unit="%" />
            <Tooltip content={<Tip unit="%" />} />
            {picked.map((id, i) => (
              <Line key={id} type="monotone" dataKey={byId[id].label} stroke={SERIES[i % MAX_SERIES]}
                strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: 'var(--surface-1)' }} activeDot={{ r: 6 }}>
                <LabelList dataKey={byId[id].label} position="right" fontSize={11}
                  fill={SERIES[i % MAX_SERIES]}
                  formatter={(v) => (v === data.at(-1)[byId[id].label] ? `${byId[id].label} ${v}%` : '')} />
              </Line>
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
        <thead><tr><th>Concept</th><th className="num">2026</th><th className="num">2027</th><th className="num">Change</th></tr></thead>
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
        Change in share of submissions from ICLR 2026 to ICLR 2027, in percentage points.
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
      <h2>How ICLR 2027 is scoring papers</h2>
      <p className="note">
        ICLR 2027 moved to a <strong>1&ndash;4 rating scale</strong>. Earlier years used 1&ndash;10
        (2024&ndash;25) and 0&ndash;10 (2026), so scores cannot be compared across years and this
        report never does.
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

function PaperTable({ rows, caption, note, showSpread }) {
  return (
    <section>
      <h2>{caption}</h2>
      <p className="note">{note}</p>
      <table>
        <thead>
          <tr>
            <th className="num">#</th><th>Paper</th>
            <th className="num">Mean</th>
            {showSpread ? <th className="num">Spread</th> : <th className="num">Reviews</th>}
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
              <td className="num">
                {showSpread
                  ? <span className="spread">{r.ratings.join(' · ')}</span>
                  : r.n}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
          <tr><th style={{ width: 190 }}>Source</th><td>The public OpenReview record for ICLR 2024&ndash;2027, fetched {meta.as_of} via the authenticated API.</td></tr>
          <tr><th>What counts</th><td>{meta.excluded_note} Analysed: {YEARS.map((y) => `${y}: ${n(meta.analysed[y])}`).join(', ')}.</td></tr>
          <tr><th>Concept labels</th><td>Each paper&rsquo;s title, keywords and abstract were labelled against {meta.n_concepts} hand-curated concepts by Claude Haiku 5.5. The concept list lives in <code>topics.json</code> in the repository and is editable.</td></tr>
          <tr><th>Label quality</th><td>Measured on 60 papers whose titles name a concept unambiguously: 100% of those concepts were recovered. 12% of all predicted labels had no matching phrase in the paper text &mdash; some are legitimate synonyms, some are wrong. Treat per-concept counts as accurate to a few percent, not exact.</td></tr>
          <tr><th>Overlap</th><td>Concepts are not mutually exclusive. A paper may carry up to three, so concept counts overlap and shares do not sum to 100%.</td></tr>
          <tr><th>Rating scales</th><td>{YEARS.map((y) => `${y}: ${meta.rating_scales[y]}`).join(', ')}. Never compared across years.</td></tr>
          <tr><th>2027 authors</th><td>Withheld &mdash; ICLR 2027 is mid-review and submissions are anonymous, so the tables above show titles without authors.</td></tr>
          <tr><th>Not shown</th><td>Acceptance rates for 2027: no decisions have been released. Withdrawal rates: withdrawals accumulate until decisions, so 2027&rsquo;s figure is not comparable with a finished year&rsquo;s.</td></tr>
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
      <Trend />
      <Movers />
      <Ratings />
      <PaperTable rows={top_papers} caption="Highest-rated submissions"
        note={`Top ${top_papers.length} of the labelled 2027 submissions by mean reviewer rating, among papers with at least three reviews. On a 1-4 scale ties are common; order within a tie is by review count. A high score here is not an acceptance - no decisions have been released.`} />
      <PaperTable rows={contested_papers} showSpread caption="Most contested submissions"
        note={`The ${contested_papers.length} papers whose reviewers disagreed most, by standard deviation of their ratings. The Spread column lists the individual ratings.`} />
      <Method />
      <footer>
        Built from public OpenReview data. Not affiliated with ICLR or OpenReview.
        Pipeline and concept list: <a href="https://github.com/Wongi-Jang/iclr2027-report">github.com/Wongi-Jang/iclr2027-report</a>.
      </footer>
    </div>
  )
}
