"use client";
import { FormEvent, useEffect, useState } from "react";

type Product = {
  id: number;
  name: string;
  description: string | null;
  price: number;
};

const API_URL = "http://127.0.0.1:8001";

export default function JwtPage() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState("");

  const [regUsername, setRegUsername] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [message, setMessage] = useState("");
  const [lockedSeconds, setLockedSeconds] = useState(0);

  const [products, setProducts] = useState<Product[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editPrice, setEditPrice] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("jwt_token");
    const savedUser = localStorage.getItem("jwt_username");
    if (saved) setToken(saved);
    if (savedUser) setUsername(savedUser);
  }, []);

  useEffect(() => {
    if (lockedSeconds <= 0) return;
    const timer = setTimeout(() => setLockedSeconds(lockedSeconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [lockedSeconds]);

  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/products`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        const result = await res.json();
        if (res.status === 401) {
          // saved token expired or was revoked - back to the login screen
          setToken(null);
          setUsername("");
          localStorage.removeItem("jwt_token");
          localStorage.removeItem("jwt_username");
          setMessage("Session expired, please log in again");
          return;
        }
        if (!res.ok) {
          setMessage(result.detail || "Failed to load products");
          return;
        }
        setProducts(result);
      })
      .catch(() => setMessage("Failed to load products"));
  }, [token]);

  async function register(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const res = await fetch(`${API_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: regUsername, password: regPassword }),
    });
    const result = await res.json();
    if (!res.ok) {
      setMessage(result.detail || "Failed to register");
      return;
    }
    setMessage(`Registered "${result.username}" - now log in`);
    setRegUsername("");
    setRegPassword("");
  }

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const body = new URLSearchParams();
    body.set("username", loginUsername);
    body.set("password", loginPassword);

    const res = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const result = await res.json();
    if (res.status === 429) {
      setLockedSeconds(Number(res.headers.get("Retry-After")) || 60);
    }
    if (!res.ok) {
      setMessage(result.detail || "Failed to log in");
      return;
    }
    setToken(result.access_token);
    setUsername(loginUsername);
    localStorage.setItem("jwt_token", result.access_token);
    localStorage.setItem("jwt_username", loginUsername);
    setLoginUsername("");
    setLoginPassword("");
    setMessage("");
  }

  async function logout() {
    if (token) {
      await fetch(`${API_URL}/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    }
    setToken(null);
    setUsername("");
    setProducts([]);
    localStorage.removeItem("jwt_token");
    localStorage.removeItem("jwt_username");
  }

  async function addProduct(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const res = await fetch(`${API_URL}/products`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ name, description, price: Number(price) }),
    });
    const result = await res.json();
    if (!res.ok) {
      setMessage(result.detail || "Failed to add product");
      return;
    }
    setProducts([...products, result]);
    setName("");
    setDescription("");
    setPrice("");
    setMessage("");
  }

  async function deleteProduct(productId: number) {
    const res = await fetch(`${API_URL}/products/${productId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    setProducts(products.filter((p) => p.id !== productId));
  }

  function startEdit(product: Product) {
    setEditingId(product.id);
    setEditName(product.name);
    setEditDescription(product.description ?? "");
    setEditPrice(String(product.price));
  }

  async function saveEdit(productId: number) {
    const res = await fetch(`${API_URL}/products/${productId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: editName,
        description: editDescription,
        price: Number(editPrice),
      }),
    });
    const result = await res.json();
    if (!res.ok) {
      setMessage(result.detail || "Failed to update product");
      return;
    }
    setProducts(products.map((p) => (p.id === productId ? result : p)));
    setEditingId(null);
  }

  if (!token) {
    return (
      <main>
        <h1>JWT Demo</h1>

        {message && <p>{message}</p>}

        <h2>Register</h2>
        <form onSubmit={register}>
          <input
            placeholder="Username"
            value={regUsername}
            onChange={(e) => setRegUsername(e.target.value)}
            required
          />
          <input
            placeholder="Password"
            type="password"
            value={regPassword}
            onChange={(e) => setRegPassword(e.target.value)}
            required
          />
          <button type="submit">Register</button>
        </form>

        <h2>Login</h2>
        <form onSubmit={login}>
          <input
            placeholder="Username"
            value={loginUsername}
            onChange={(e) => setLoginUsername(e.target.value)}
            required
          />
          <input
            placeholder="Password"
            type="password"
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={lockedSeconds > 0}>
            {lockedSeconds > 0 ? `Locked (${lockedSeconds}s)` : "Login"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <main>
      <h1>Products</h1>
      <p>
        Logged in as {username} <button onClick={logout}>Logout</button>
      </p>

      {message && <p>{message}</p>}

      <form onSubmit={addProduct}>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input
          placeholder="Price"
          type="number"
          step="0.01"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          required
        />
        <button type="submit">Add</button>
      </form>

      <ul>
        {products.map((product) => (
          <li key={product.id}>
            {editingId === product.id ? (
              <>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} />
                <input
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                />
                <input
                  type="number"
                  step="0.01"
                  value={editPrice}
                  onChange={(e) => setEditPrice(e.target.value)}
                  style={{ width: "5rem" }}
                />
                <button onClick={() => saveEdit(product.id)}>Save</button>
                <button onClick={() => setEditingId(null)}>Cancel</button>
              </>
            ) : (
              <>
                {product.name} (ID {product.id}) - {product.description} - ${product.price}
                <button onClick={() => startEdit(product)}>Edit</button>
                <button onClick={() => deleteProduct(product.id)}>Delete</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
