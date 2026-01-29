import { useEffect, useState } from "react";
import API from "../services/api";

export default function Dashboard() {
  const [stats, setStats] = useState({});

  useEffect(() => {
    API.get("/api/dashboard/pipeline")
      .then(res => setStats(res.data));
  }, []);

  return (
    <div>
      <h2>Pipeline</h2>
      {Object.keys(stats).map(key => (
        <p key={key}>{key}: {stats[key]}</p>
      ))}
    </div>
  );
}
