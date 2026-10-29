"use client";
import { FormEvent, useEffect, useState } from "react";

type Student = {
  id: number;
  name: string;
  score: number;
};

const API_URL = "http://127.0.0.1:8000/students";

export default function Home() {
  const [students, setStudents] = useState<Student[]>([]);
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [score, setScore] = useState("");
  const [message, setMessage] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editScore, setEditScore] = useState("");

  useEffect(() => {
    fetch(API_URL)
      .then((res) => res.json())
      .then((data) => {
        // a wrong/missing backend returns an error object, not a list
        if (!Array.isArray(data)) throw new Error();
        setStudents(data);
      })
      .catch(() => setMessage("Failed to load students"));
  }, []);

  async function addStudent(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: Number(id), name, score: Number(score) }),
    });
    const result = await res.json();
    if (!res.ok) {
      setMessage(result.detail || "Failed to add student");
      return;
    }
    setStudents([...students, result]);
    setId("");
    setName("");
    setScore("");
    setMessage("");
  }

  async function deleteStudent(studentId: number) {
    const res = await fetch(`${API_URL}/${studentId}`, { method: "DELETE" });
    if (!res.ok) return;
    setStudents(students.filter((s) => s.id !== studentId));
  }

  function startEdit(student: Student) {
    setEditingId(student.id);
    setEditScore(String(student.score));
  }

  async function saveEdit(student: Student) {
    const res = await fetch(`${API_URL}/${student.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...student, score: Number(editScore) }),
    });
    const result = await res.json();
    if (!res.ok) return;
    setStudents(students.map((s) => (s.id === student.id ? result.data : s)));
    setEditingId(null);
  }

  return (
    <main>
      <h1>Student Records</h1>

      {message && <p>{message}</p>}

      <form onSubmit={addStudent}>
        <input placeholder="ID" type="number" value={id} onChange={(e) => setId(e.target.value)} required />
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="Score" type="number" value={score} onChange={(e) => setScore(e.target.value)} required />
        <button type="submit">Add</button>
      </form>

      <ul>
        {students.map((student) => (
          <li key={student.id}>
            {student.name} (ID {student.id}) -{" "}
            {editingId === student.id ? (
              <>
                <input
                  type="number"
                  value={editScore}
                  onChange={(e) => setEditScore(e.target.value)}
                  style={{ width: "3rem" }}
                />
                <button onClick={() => saveEdit(student)}>Save</button>
                <button onClick={() => setEditingId(null)}>Cancel</button>
              </>
            ) : (
              <>
                {student.score}
                <button onClick={() => startEdit(student)}>Edit</button>
                <button onClick={() => deleteStudent(student.id)}>Delete</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}