import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

type EspState = { up: boolean; down: boolean };

export default function App() {
  const [upOn, setUpOn] = useState(false);
  const [downOn, setDownOn] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const [loading, setLoading] = useState<{ up: boolean; down: boolean }>({
    up: false,
    down: false,
  });
  const [error, setError] = useState("");

  const updatedLabel = useMemo(() => {
    if (!updatedAt) return "—";
    const d = new Date(updatedAt);
    return isNaN(d.getTime()) ? updatedAt : d.toLocaleString();
  }, [updatedAt]);

  const refresh = async () => {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/state`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as EspState;

      setUpOn(Boolean(data.up));
      setDownOn(Boolean(data.down));
      setUpdatedAt(new Date().toISOString());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const setRelay = async (which: "up" | "down", on: boolean) => {
    setLoading((s) => ({ ...s, [which]: true }));
    setError("");
    try {
      const endpoint =
        which === "up"
          ? on
            ? "/up/on"
            : "/up/off"
          : on
            ? "/down/on"
            : "/down/off";

      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Read back actual state from ESP
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading((s) => ({ ...s, [which]: false }));
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="page">
      <div className="stack">
        {/* REGION: UP */}
        <div className="card">
          <header className="header">
            <div>
              <h1>Calefacción</h1>
              <p className="sub">Zona: arriba</p>
            </div>
            <span className={`badge ${upOn ? "on" : "off"}`}>
              {upOn ? "ENCENDIDA" : "APAGADA"}
            </span>
          </header>

          <div className="meta">
            <span>Última actualización</span>
            <strong>{updatedLabel}</strong>
          </div>

          {error && <div className="error">⚠️ {error}</div>}

          <div className="grid">
            <button
              className="btn primary"
              disabled={loading.up || upOn}
              onClick={() => setRelay("up", true)}
            >
              Encender
            </button>
            <button
              className="btn dark"
              disabled={loading.up || !upOn}
              onClick={() => setRelay("up", false)}
            >
              Apagar
            </button>
          </div>

          <button className="btn outline" disabled={loading.up || loading.down} onClick={refresh}>
            Refrescar
          </button>
        </div>

        {/* REGION: DOWN */}
        <div className="card">
          <header className="header">
            <div>
              <h1>Calefacción</h1>
              <p className="sub">Zona: abajo</p>
            </div>
            <span className={`badge ${downOn ? "on" : "off"}`}>
              {downOn ? "ENCENDIDA" : "APAGADA"}
            </span>
          </header>

          <div className="meta">
            <span>Última actualización</span>
            <strong>{updatedLabel}</strong>
          </div>

          {error && <div className="error">⚠️ {error}</div>}

          <div className="grid">
            <button
              className="btn primary"
              disabled={loading.down || downOn}
              onClick={() => setRelay("down", true)}
            >
              Encender
            </button>
            <button
              className="btn dark"
              disabled={loading.down || !downOn}
              onClick={() => setRelay("down", false)}
            >
              Apagar
            </button>
          </div>

          <button className="btn outline" disabled={loading.up || loading.down} onClick={refresh}>
            Refrescar
          </button>
        </div>
      </div>
    </div>
  );
}
