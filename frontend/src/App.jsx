import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, Area, AreaChart, BarChart, Bar, Cell,
} from 'recharts';

const API = '/api';

async function getJson(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function App() {
  const [departments, setDepartments] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [forecastDept, setForecastDept] = useState('ALL');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [deps, snap] = await Promise.all([
          getJson('/departments'),
          getJson('/snapshot'),
        ]);
        setDepartments(deps);
        setSnapshot(snap);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const fc = await getJson(`/forecast?dept=${forecastDept}&horizon_h=72`);
        setForecast(fc.points || []);
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [forecastDept]);

  if (loading) return <div style={{ padding: 24 }}>Loading twin…</div>;

  const lastStep = snapshot && snapshot.steps ? snapshot.steps[snapshot.steps.length - 1] : null;
  const overallUtil = lastStep ? (lastStep.overall_utilization * 100).toFixed(0) : '—';
  const totalOcc = lastStep ? lastStep.total_occupied : 0;
  const totalBeds = lastStep ? lastStep.total_beds : 0;

  const deptStates = lastStep ? lastStep.departments : [];
  const totalArrivals = deptStates.reduce((s, d) => s + d.arrivals, 0);
  const totalBlocked = deptStates.reduce((s, d) => s + d.blocked, 0);

  const series = snapshot && snapshot.steps
    ? snapshot.steps.map((s) => ({
        t: (s.t / 24).toFixed(1),
        occupancy: s.total_occupied,
      }))
    : [];

  return (
    <>
      <header>
        <h1>MedOps Twin <span className="badge">Digital Twin</span></h1>
        <span className="refresh-dot" title="live" />
        <span>Live synthetic feed</span>
      </header>
      <main>
        {error && <div className="panel" style={{ borderColor: 'var(--red)' }}>API error: {error}</div>}

        <div className="grid kpi-row">
          <div className="panel kpi"><div className="value">{overallUtil}%</div><div className="label">Overall bed utilization</div></div>
          <div className="panel kpi"><div className="value">{totalOcc}/{totalBeds}</div><div className="label">Beds occupied / total</div></div>
          <div className="panel kpi"><div className="value">{totalArrivals}</div><div className="label">Total arrivals</div></div>
          <div className="panel kpi"><div className="value" style={{ color: totalBlocked ? 'var(--red)' : 'var(--green)' }}>{totalBlocked}</div><div className="label">Blocked / turned away</div></div>
        </div>

        <div className="grid two-col">
          <div className="panel">
            <h2>Occupancy over time (steps)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="occ" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.6} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="t" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                <Area type="monotone" dataKey="occupancy" stroke="#38bdf8" fill="url(#occ)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="panel">
            <h2>Occupancy forecast</h2>
            <div style={{ marginBottom: 8 }}>
              <select value={forecastDept} onChange={(e) => setForecastDept(e.target.value)}>
                <option value="ALL">All departments</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={forecast}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey={(p) => (p.t / 24).toFixed(1)} stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                <Line type="monotone" dataKey="predicted_occupancy" stroke="#34d399" dot={false} name="forecast" />
                <Line type="monotone" dataKey="upper" stroke="#fbbf24" strokeDasharray="4 4" dot={false} name="upper" />
                <Line type="monotone" dataKey="lower" stroke="#fbbf24" strokeDasharray="4 4" dot={false} name="lower" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid two-col">
          <div className="panel">
            <h2>Department load</h2>
            {deptStates.map((d) => {
              const util = d.beds.utilization;
              const cls = util >= 0.9 ? 'crit' : util >= 0.75 ? 'warn' : '';
              return (
                <div key={d.id} className="dept-row">
                  <div>
                    <div className="name">{d.name}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      {d.beds.occupied}/{d.beds.total} beds · {d.blocked} blocked
                    </div>
                  </div>
                  <div style={{ width: '40%' }}>
                    <div className="bar-wrap">
                      <div className={`bar ${cls}`} style={{ width: `${(util * 100).toFixed(0)}%` }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="panel">
            <h2>Arrivals by department</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={deptStates}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="id" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                <Bar dataKey="arrivals" fill="#38bdf8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>
    </>
  );
}

export default App;
