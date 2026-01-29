import { useEffect, useState } from "react";
import API from "../services/api";

export default function Candidates() {
  const [candidates, setCandidates] = useState([]);

  useEffect(() => {
    API.get("/api/candidates?status=APPLIED")
      .then(res => setCandidates(res.data));
  }, []);

  return (
    <div>
      <h2>Candidates</h2>
      <ul>
        {candidates.map(c => (
          <li key={c.id}>
            {c.fullName} — {c.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
