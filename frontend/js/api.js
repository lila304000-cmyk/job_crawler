const API_BASE = "/api";

const defaultOptions = {
  headers: {
    "Content-Type": "application/json",
  },
};

function getToken() {
  return localStorage.getItem("token") || "";
}

async function request(method, url, body = null, params = null) {
  const fullUrl = new URL(API_BASE + url, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) fullUrl.searchParams.append(k, v);
    });
  }

  const token = getToken();
  const options = {
    method,
    headers: {
      ...defaultOptions.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const resp = await fetch(fullUrl.toString(), options);
  if (resp.status === 401) {
    localStorage.removeItem("token");
    window.location.hash = "login";
    throw new Error("登录已过期，请重新登录");
  }

  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.message || `请求失败: ${resp.status}`);
  }
  return data;
}

const api = {
  // 认证
  login(username, password) {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    return fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    }).then(async (resp) => {
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.message || "登录失败");
      }
      return resp.json();
    });
  },

  me() {
    return request("GET", "/auth/me");
  },

  // 渠道
  listChannels(params) {
    return request("GET", "/channels", null, params);
  },
  getChannel(id) {
    return request("GET", `/channels/${id}`);
  },
  createChannel(data) {
    return request("POST", "/channels", data);
  },
  updateChannel(id, data) {
    return request("PUT", `/channels/${id}`, data);
  },
  deleteChannel(id) {
    return request("DELETE", `/channels/${id}`);
  },

  // 任务
  listTasks(params) {
    return request("GET", "/tasks", null, params);
  },
  getTask(id) {
    return request("GET", `/tasks/${id}`);
  },
  createTask(data) {
    return request("POST", "/tasks", data);
  },
  updateTask(id, data) {
    return request("PUT", `/tasks/${id}`, data);
  },
  deleteTask(id) {
    return request("DELETE", `/tasks/${id}`);
  },
  runTask(id) {
    return request("POST", `/tasks/${id}/run`);
  },
  listTaskLogs(id, limit = 50) {
    return request("GET", `/tasks/${id}/logs`, null, { limit });
  },
};
