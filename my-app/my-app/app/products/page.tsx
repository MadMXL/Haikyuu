"use client";
import { FormEvent, useEffect, useMemo, useState } from "react";

type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  quantity: number;
  image: string | null;
  status: "available" | "reserved" | "sold";
};

// a hold this browser placed: the token is needed to confirm, expiresAt drives the countdown
type Reservation = { token: string; amount: number; expiresAt: number };

function startReservation(token: string, amount: number, expiresIn: number): Reservation {
  return { token, amount, expiresAt: Date.now() + expiresIn * 1000 };
}

const AUTH_URL = "http://127.0.0.1:8000";
const API_URL = "http://127.0.0.1:8000/products/";
const IMAGE_URL = "http://127.0.0.1:8000/images/";
const SESSION_EXPIRED = "Session expired, please log in again";

type AuthFetch = (url: string, init?: RequestInit) => Promise<Response>;

// keeps "session expired" visible instead of replacing it with a generic error
function errorMessage(err: unknown, fallback: string) {
  return err instanceof Error && err.message === SESSION_EXPIRED ? SESSION_EXPIRED : fallback;
}

const inputClass =
  "w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-neutral-900 focus:ring-2 focus:ring-neutral-900/10";
const primaryButton =
  "rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white no-underline transition hover:bg-neutral-700 disabled:opacity-50";
const secondaryButton =
  "rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-sm font-medium text-neutral-800 no-underline transition hover:bg-neutral-100 disabled:opacity-50";
const smallSecondaryButton =
  "rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs font-medium text-neutral-800 no-underline transition hover:bg-neutral-100 disabled:opacity-50";
const smallPrimaryButton =
  "rounded-md bg-neutral-900 px-2 py-1 text-xs font-medium text-white no-underline transition hover:bg-neutral-700 disabled:opacity-50";
const smallDangerButton =
  "rounded-md px-2 py-1 text-xs font-medium text-red-600 no-underline transition hover:bg-red-50 disabled:opacity-50";

// sends the picked file to the product's image endpoint; returns the updated product
async function uploadImage(authFetch: AuthFetch, productId: number, file: File): Promise<Product> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await authFetch(`${API_URL}${productId}/image`, { method: "POST", body: formData });
  const result = await res.json();
  if (!res.ok) throw new Error(result.detail || "Failed to upload image");
  return result;
}

function formatPrice(price: number) {
  return `$${price.toFixed(2)}`;
}

const statusBadge: Record<Product["status"], string> = {
  available: "bg-green-100 text-green-700",
  reserved: "bg-amber-100 text-amber-700",
  sold: "bg-neutral-200 text-neutral-600",
};

// square image slot: shows the newly picked file, else the current image, else a placeholder;
// clicking it opens the file picker
function ImagePicker({
  file,
  currentUrl,
  onChange,
}: {
  file: File | null;
  currentUrl?: string | null;
  onChange: (file: File | null) => void;
}) {
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const shown = previewUrl ?? currentUrl;

  return (
    <label className="group relative flex aspect-square w-full cursor-pointer items-center justify-center overflow-hidden rounded-lg border border-dashed border-neutral-300 bg-neutral-50 transition hover:border-neutral-500">
      {shown ? (
        <>
          <img src={shown} alt="" className="h-full w-full object-cover" />
          <span className="absolute inset-0 flex items-center justify-center bg-black/40 text-sm font-medium text-white opacity-0 transition group-hover:opacity-100">
            Change image
          </span>
        </>
      ) : (
        <span className="px-2 text-center text-sm text-neutral-500">+ Add image</span>
      )}
      <input
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          onChange(e.target.files?.[0] ?? null);
          e.target.value = ""; // lets the same file be picked again
        }}
      />
    </label>
  );
}

// login / register card; 5 wrong passwords in a minute locks the button for a bit
function LoginForm({
  notice,
  onLogin,
}: {
  notice: string;
  onLogin: (token: string, username: string) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(notice);
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [lockedSeconds, setLockedSeconds] = useState(0);

  useEffect(() => {
    if (lockedSeconds <= 0) return;
    const timer = setTimeout(() => setLockedSeconds(lockedSeconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [lockedSeconds]);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    try {
      if (mode === "register") {
        const res = await fetch(`${AUTH_URL}/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        const result = await res.json();
        if (!res.ok) {
          setError(result.detail || "Failed to register");
          return;
        }
        setInfo(`Registered "${result.username}" - now log in`);
        setMode("login");
        setPassword("");
        return;
      }

      const res = await fetch(`${AUTH_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });
      const result = await res.json();
      if (res.status === 429) {
        setLockedSeconds(Number(res.headers.get("Retry-After")) || 60);
      }
      if (!res.ok) {
        setError(result.detail || "Failed to log in");
        return;
      }
      onLogin(result.access_token, username);
    } catch {
      setError("Can't reach the backend. Is it running on port 8000?");
    } finally {
      setBusy(false);
    }
  }

  const locked = mode === "login" && lockedSeconds > 0;
  const tabClass = (active: boolean) =>
    `rounded-md px-3 py-1 text-sm font-medium no-underline transition ${
      active ? "bg-white text-neutral-900 shadow-sm" : "text-neutral-500 hover:text-neutral-800"
    }`;

  return (
    <section className="mb-8 rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-medium">{mode === "login" ? "Log in" : "Create an account"}</h2>
        <div className="flex gap-1 rounded-lg bg-neutral-100 p-1">
          <button type="button" className={tabClass(mode === "login")} onClick={() => setMode("login")}>
            Log in
          </button>
          <button
            type="button"
            className={tabClass(mode === "register")}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>
      </div>

      {error && (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {info && (
        <p className="mb-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {info}
        </p>
      )}

      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-neutral-700">Username</span>
          <input
            className={inputClass}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-neutral-700">Password</span>
          <input
            className={inputClass}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
          />
        </label>
        <button type="submit" className={primaryButton} disabled={busy || locked}>
          {locked
            ? `Locked (${lockedSeconds}s)`
            : busy
              ? "Please wait…"
              : mode === "login"
                ? "Log in"
                : "Create account"}
        </button>
      </form>
    </section>
  );
}

function CorsDemo() {
  const [result, setResult] = useState("waiting...");

  async function callHeadFoo() {
    try {
      const res = await fetch("http://127.0.0.1:8000/foo", {
        method: "HEAD",
        headers: { "X-Homework": "cors-head" },
      });
      setResult("HEAD ok: status " + res.status);
    } catch (err) {
      setResult("CORS Error: " + err + "\n(open DevTools > Console for full details)");
    }
  }

  return (
    <section className="mt-10 rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <h2 className="mb-2 text-lg font-medium">CORS HEAD Demo</h2>
      <p className="mb-3 text-sm text-neutral-500">
        HEAD is not in <code>allow_methods</code> — clicking the button triggers a CORS error.
      </p>
      <button className={primaryButton} onClick={callHeadFoo}>
        Call HEAD /foo
      </button>
      <pre className="mt-3 rounded-lg bg-neutral-50 p-3 text-xs text-neutral-700 whitespace-pre-wrap">{result}</pre>
    </section>
  );
}

export default function ProductsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [authNotice, setAuthNotice] = useState("");

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [editQuantity, setEditQuantity] = useState("");
  const [editImage, setEditImage] = useState<File | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [reservations, setReservations] = useState<Record<number, Reservation>>({});
  const [now, setNow] = useState(() => Date.now());
  // how many units each card's "Reserve" button asks for
  const [amounts, setAmounts] = useState<Record<number, string>>({});

  useEffect(() => {
    // localStorage only exists in the browser, so the saved login is read after mount
    const saved = localStorage.getItem("products_token");
    if (saved) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setToken(saved);
      setUsername(localStorage.getItem("products_username") ?? "");
    }
  }, []);

  function clearSession(notice = "") {
    setToken(null);
    setUsername("");
    setProducts([]);
    setEditingId(null);
    setReservations({});
    setMessage("");
    setAuthNotice(notice);
    localStorage.removeItem("products_token");
    localStorage.removeItem("products_username");
  }

  // fetch with the JWT attached; a 401 means the token expired or was revoked
  const authFetch: AuthFetch = async (url, init = {}) => {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(url, { ...init, headers });
    if (res.status === 401) {
      clearSession(SESSION_EXPIRED);
      throw new Error(SESSION_EXPIRED);
    }
    return res;
  };

  function handleLogin(newToken: string, newUsername: string) {
    localStorage.setItem("products_token", newToken);
    localStorage.setItem("products_username", newUsername);
    setAuthNotice("");
    setLoading(true);
    setUsername(newUsername);
    setToken(newToken);
  }

  async function logout() {
    // tell the backend to blacklist the token; log out locally either way
    await authFetch(`${AUTH_URL}/logout`, { method: "POST" }).catch(() => {});
    clearSession();
  }

  useEffect(() => {
    if (!token) return;
    fetch(API_URL, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (res.status === 401) throw new Error(SESSION_EXPIRED);
        if (!res.ok) throw new Error();
        return res.json();
      })
      .then(setProducts)
      .catch((err) => {
        if (errorMessage(err, "") === SESSION_EXPIRED) clearSession(SESSION_EXPIRED);
        else setMessage("Failed to load products. Is the backend running on port 8000?");
      })
      .finally(() => setLoading(false));
  }, [token]);

  // tick once a second while this browser holds a reservation
  const holding = Object.keys(reservations).length > 0;
  useEffect(() => {
    if (!holding) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [holding]);

  // the server is the source of truth for quantity, so re-read the product after every change
  async function refreshProduct(productId: number) {
    const res = await authFetch(`${API_URL}${productId}`);
    if (!res.ok) return;
    const latest: Product = await res.json();
    setProducts((prev) => prev.map((p) => (p.id === productId ? latest : p)));
  }

  function dropReservation(productId: number) {
    setReservations((prev) => {
      const next = { ...prev };
      delete next[productId];
      return next;
    });
  }

  // an unconfirmed hold ran out: the server has rolled the quantity back, so show it again
  useEffect(() => {
    const expired = Object.entries(reservations)
      .filter(([, r]) => r.expiresAt <= now)
      .map(([id]) => Number(id));
    if (expired.length === 0) return;
    expired.forEach((id) => {
      dropReservation(id);
      refreshProduct(id).catch(() => {});
    });
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMessage("Reservation expired - the quantity was put back");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [now, reservations]);

  async function reserveProduct(product: Product) {
    const amount = Number(amounts[product.id] ?? 1);
    setBusyId(product.id);
    try {
      const res = await authFetch(`${API_URL}${product.id}/reserve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      const result = await res.json();
      if (!res.ok) {
        setMessage(typeof result.detail === "string" ? result.detail : "Failed to reserve product");
        await refreshProduct(product.id);
        return;
      }
      const reservation = startReservation(result.reservation_token, result.amount, result.expires_in);
      setNow(reservation.expiresAt - result.expires_in * 1000);
      setReservations((prev) => ({ ...prev, [product.id]: reservation }));
      setMessage("");
      await refreshProduct(product.id);
    } catch (err) {
      setMessage(errorMessage(err, "Failed to reserve product"));
    } finally {
      setBusyId(null);
    }
  }

  // "confirm" makes the sale final, "cancel" gives the reserved quantity back right away
  async function finishReservation(product: Product, action: "confirm" | "cancel") {
    const reservation = reservations[product.id];
    if (!reservation) return;
    setBusyId(product.id);
    try {
      const res = await authFetch(`${API_URL}${product.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reservation_token: reservation.token }),
      });
      const result = await res.json();
      dropReservation(product.id);
      setMessage(res.ok ? "" : result.detail || `Failed to ${action}`);
      await refreshProduct(product.id);
    } catch (err) {
      setMessage(errorMessage(err, `Failed to ${action}`));
    } finally {
      setBusyId(null);
    }
  }

  async function addProduct(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAdding(true);
    try {
      const res = await authFetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description, price: Number(price), quantity: Number(quantity) }),
      });
      const result = await res.json();
      if (!res.ok) {
        setMessage(result.detail || "Failed to add product");
        return;
      }
      let product: Product = result;
      try {
        if (image) product = await uploadImage(authFetch, product.id, image);
        setMessage("");
      } catch (err) {
        setMessage((err as Error).message);
      }
      setProducts((prev) => [...prev, product]);
      setName("");
      setDescription("");
      setPrice("");
      setQuantity("");
      setImage(null);
    } catch (err) {
      setMessage(errorMessage(err, "Failed to add product"));
    } finally {
      setAdding(false);
    }
  }

  async function deleteProduct(product: Product) {
    if (!window.confirm(`Delete "${product.name}"?`)) return;
    setBusyId(product.id);
    try {
      const res = await authFetch(`${API_URL}${product.id}`, { method: "DELETE" });
      if (!res.ok) {
        setMessage("Failed to delete product");
        return;
      }
      setProducts((prev) => prev.filter((p) => p.id !== product.id));
    } catch (err) {
      setMessage(errorMessage(err, "Failed to delete product"));
    } finally {
      setBusyId(null);
    }
  }

  function startEdit(product: Product) {
    setEditingId(product.id);
    setEditName(product.name);
    setEditDescription(product.description);
    setEditPrice(String(product.price));
    setEditQuantity(String(product.quantity));
    setEditImage(null);
  }

  async function saveEdit(productId: number) {
    setBusyId(productId);
    try {
      const res = await authFetch(`${API_URL}${productId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName,
          description: editDescription,
          price: Number(editPrice),
          quantity: Number(editQuantity),
        }),
      });
      const result = await res.json();
      if (!res.ok) {
        setMessage(result.detail || "Failed to update product");
        return;
      }
      let product: Product = result;
      try {
        if (editImage) product = await uploadImage(authFetch, productId, editImage);
        setMessage("");
      } catch (err) {
        setMessage((err as Error).message);
      }
      setProducts((prev) => prev.map((p) => (p.id === productId ? product : p)));
      setEditingId(null);
    } catch (err) {
      setMessage(errorMessage(err, "Failed to update product"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
      <header className="mb-8 flex flex-wrap items-baseline justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Products</h1>
          {token && !loading && (
            <span className="text-sm text-neutral-500">
              {products.length} {products.length === 1 ? "item" : "items"}
            </span>
          )}
        </div>
        {token && (
          <div className="flex items-center gap-3 text-sm text-neutral-600">
            <span>
              Signed in as <span className="font-medium text-neutral-900">{username}</span>
            </span>
            <button className={secondaryButton} onClick={logout}>
              Log out
            </button>
          </div>
        )}
      </header>

      {message && (
        <div className="mb-6 flex items-start justify-between gap-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span>{message}</span>
          <button
            onClick={() => setMessage("")}
            className="p-0 text-red-700 no-underline hover:text-red-900"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {!token ? (
        <>
          <LoginForm notice={authNotice} onLogin={handleLogin} />
          <p className="rounded-xl border border-dashed border-neutral-300 py-16 text-center text-sm text-neutral-500">
            Log in above to see and manage products.
          </p>
        </>
      ) : (
        <>
          <section className="mb-8 rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
            <h2 className="mb-4 text-lg font-medium">Add a product</h2>
            <form onSubmit={addProduct} className="flex flex-col gap-4 sm:flex-row">
              <div className="w-28 shrink-0">
                <ImagePicker file={image} onChange={setImage} />
              </div>
              <div className="flex flex-1 flex-col gap-3">
                <div className="grid gap-3 sm:grid-cols-[1fr_9rem_7rem]">
                  <label className="text-sm">
                    <span className="mb-1 block font-medium text-neutral-700">Name</span>
                    <input
                      className={inputClass}
                      placeholder="e.g. Coffee mug"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    <span className="mb-1 block font-medium text-neutral-700">Price</span>
                    <input
                      className={inputClass}
                      placeholder="0.00"
                      type="number"
                      step="0.01"
                      min="0"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      required
                    />
                  </label>
                  <label className="text-sm">
                    <span className="mb-1 block font-medium text-neutral-700">Quantity</span>
                    <input
                      className={inputClass}
                      placeholder="0"
                      type="number"
                      step="1"
                      min="0"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      required
                    />
                  </label>
                </div>
                <label className="text-sm">
                  <span className="mb-1 block font-medium text-neutral-700">Description</span>
                  <textarea
                    className={`${inputClass} min-h-14 resize-y`}
                    placeholder="A short description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                  />
                </label>
                <div className="flex justify-end">
                  <button type="submit" className={primaryButton} disabled={adding}>
                    {adding ? "Adding…" : "Add product"}
                  </button>
                </div>
              </div>
            </form>
          </section>

          {loading ? (
            <p className="py-16 text-center text-sm text-neutral-500">Loading products…</p>
          ) : products.length === 0 ? (
            <p className="rounded-xl border border-dashed border-neutral-300 py-16 text-center text-sm text-neutral-500">
              No products yet. Add your first one above.
            </p>
          ) : (
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {products.map((product) => {
                const imageUrl = product.image ? `${IMAGE_URL}${product.image}` : null;
                const busy = busyId === product.id;
                const reservation = reservations[product.id];
                const secondsLeft = reservation
                  ? Math.max(0, Math.ceil((reservation.expiresAt - now) / 1000))
                  : 0;
                // checked before sending; the server still enforces the same limit
                const wanted = Number(amounts[product.id] ?? 1);
                const amountProblem =
                  wanted > product.quantity
                    ? `Over the limit: only ${product.quantity} left to reserve`
                    : !Number.isInteger(wanted) || wanted < 1
                      ? "Enter a whole number of at least 1"
                      : "";

                if (editingId === product.id) {
                  return (
                    <li
                      key={product.id}
                      className="flex flex-col gap-2 rounded-xl border border-neutral-900 bg-white p-3 shadow-sm"
                    >
                      <ImagePicker file={editImage} currentUrl={imageUrl} onChange={setEditImage} />
                      <input
                        className={inputClass}
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        aria-label="Name"
                      />
                      <textarea
                        className={`${inputClass} min-h-16 resize-y`}
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        aria-label="Description"
                      />
                      <input
                        className={inputClass}
                        type="number"
                        step="0.01"
                        min="0"
                        value={editPrice}
                        onChange={(e) => setEditPrice(e.target.value)}
                        aria-label="Price"
                      />
                      <input
                        className={inputClass}
                        type="number"
                        step="1"
                        min="0"
                        value={editQuantity}
                        onChange={(e) => setEditQuantity(e.target.value)}
                        aria-label="Quantity"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          className={secondaryButton}
                          onClick={() => setEditingId(null)}
                          disabled={busy}
                        >
                          Cancel
                        </button>
                        <button
                          className={primaryButton}
                          onClick={() => saveEdit(product.id)}
                          disabled={busy}
                        >
                          {busy ? "Saving…" : "Save"}
                        </button>
                      </div>
                    </li>
                  );
                }

                return (
                  <li
                    key={product.id}
                    className="flex flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm transition hover:shadow-md"
                  >
                    <div className="aspect-[4/3] bg-neutral-100">
                      {imageUrl ? (
                        <img src={imageUrl} alt={product.name} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full items-center justify-center text-sm text-neutral-400">
                          No image
                        </div>
                      )}
                    </div>
                    <div className="flex flex-1 flex-col gap-1 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="truncate text-sm font-medium">{product.name}</h3>
                        <span className="text-sm font-semibold">{formatPrice(product.price)}</span>
                      </div>
                      <p className="line-clamp-2 flex-1 text-xs text-neutral-600">{product.description}</p>
                      <div className="mt-2 flex items-center justify-between gap-2">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusBadge[product.status]}`}
                        >
                          {product.status}
                        </span>
                        <span className="text-xs text-neutral-500">{product.quantity} left</span>
                      </div>
                      {reservation ? (
                        <div className="mt-2 flex flex-col gap-1 rounded-lg bg-amber-50 p-2">
                          <span className="text-xs text-amber-800">
                            You hold {reservation.amount} · {secondsLeft}s left
                          </span>
                          <div className="flex gap-1">
                            <button
                              className={`${smallPrimaryButton} flex-1`}
                              onClick={() => finishReservation(product, "confirm")}
                              disabled={busy}
                            >
                              Confirm
                            </button>
                            <button
                              className={smallSecondaryButton}
                              onClick={() => finishReservation(product, "cancel")}
                              disabled={busy}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        product.quantity > 0 && (
                          <div className="mt-2 flex flex-col gap-1">
                            <div className="flex gap-1">
                              <input
                                className={`w-14 rounded-md border px-2 py-1 text-xs ${
                                  amountProblem ? "border-red-400 bg-red-50" : "border-neutral-300"
                                }`}
                                type="number"
                                min="1"
                                max={product.quantity}
                                value={amounts[product.id] ?? "1"}
                                onChange={(e) => setAmounts((prev) => ({ ...prev, [product.id]: e.target.value }))}
                                aria-label="Amount to reserve"
                                aria-invalid={!!amountProblem}
                              />
                              <button
                                className={`${smallPrimaryButton} flex-1`}
                                onClick={() => reserveProduct(product)}
                                disabled={busy || !!amountProblem}
                              >
                                Reserve
                              </button>
                            </div>
                            {amountProblem && <span className="text-xs text-red-600">{amountProblem}</span>}
                          </div>
                        )
                      )}
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-xs text-neutral-400">ID {product.id}</span>
                        <div className="flex gap-1">
                          <button
                            className={smallSecondaryButton}
                            onClick={() => startEdit(product)}
                            disabled={busy}
                          >
                            Edit
                          </button>
                          <button
                            className={smallDangerButton}
                            onClick={() => deleteProduct(product)}
                            disabled={busy}
                          >
                            {busy ? "Deleting…" : "Delete"}
                          </button>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}

      <CorsDemo />
    </main>
  );
}
