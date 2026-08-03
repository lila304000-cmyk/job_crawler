const { createApp, ref, computed, onMounted, reactive, watch } = Vue;

/* ==================== Toast 组件 ==================== */
const ToastContainer = {
  props: ["toasts"],
  template: `
    <div class="toast-container">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
        <div style="font-weight:600">{{ t.title }}</div>
        <div style="font-size:13px;color:#6b7280">{{ t.message }}</div>
      </div>
    </div>
  `,
};

/* ==================== 登录页 ==================== */
const LoginPage = {
  emits: ["login"],
  setup(props, { emit }) {
    const username = ref("admin");
    const password = ref("admin123");
    const error = ref("");
    const loading = ref(false);

    async function submit() {
      error.value = "";
      loading.value = true;
      try {
        const res = await api.login(username.value, password.value);
        localStorage.setItem("token", res.access_token);
        emit("login");
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    return { username, password, error, loading, submit };
  },
  template: `
    <div class="login-page">
      <div class="login-card">
        <h1>Job Crawler Web</h1>
        <div class="subtitle">海外求职岗位采集系统</div>
        <form @submit.prevent="submit">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="username" placeholder="admin" required />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input v-model="password" type="password" placeholder="admin123" required />
          </div>
          <button class="btn-primary" style="width:100%" :disabled="loading">
            <span v-if="loading" class="loading"></span>
            <span v-else>登录</span>
          </button>
          <div v-if="error" class="error-msg">{{ error }}</div>
        </form>
      </div>
    </div>
  `,
};

/* ==================== 主布局 ==================== */
const MainLayout = {
  props: ["currentRoute", "currentUser"],
  emits: ["navigate", "logout"],
  setup(props, { emit }) {
    const menuItems = [
      { key: "channels", label: "渠道管理", icon: "🌐" },
      { key: "tasks", label: "采集任务", icon: "🚀" },
      { key: "jobs", label: "岗位列表", icon: "📋" },
      { key: "export", label: "Excel导出", icon: "📤" },
    ];
    return { menuItems };
  },
  template: `
    <div class="layout">
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>🕷️ Job Crawler</h2>
        </div>
        <nav class="sidebar-nav">
          <div
            v-for="item in menuItems"
            :key="item.key"
            class="nav-item"
            :class="{ active: currentRoute === item.key }"
            @click="$emit('navigate', item.key)"
          >
            <span>{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </div>
        </nav>
        <div class="sidebar-footer">
          <div>{{ currentUser }}</div>
          <button class="btn-secondary" style="margin-top:8px;width:100%" @click="$emit('logout')">退出登录</button>
        </div>
      </aside>
      <main class="main">
        <slot></slot>
      </main>
    </div>
  `,
};

/* ==================== 渠道管理页 ==================== */
const ChannelsPage = {
  emits: ["toast"],
  setup(props, { emit }) {
    const channels = ref([]);
    const loading = ref(false);
    const showModal = ref(false);
    const editingId = ref(null);

    const defaultSelectors = {
      list_container: "",
      job_card: "",
      title: "",
      company: "",
      location: "",
      salary: "",
      description: "",
      detail_link: "a[href]",
      detail_title: "h1",
      detail_company: "",
      detail_location: "",
      detail_salary: "",
      detail_description: "",
      next_page: "",
      cookie_banner: "",
      login_check: "",
    };

    const defaultRules = {
      max_pages: 5,
      max_jobs: 200,
      scroll_times: 3,
      scroll_step: 800,
      scroll_delay_ms: 1500,
      headless: true,
      use_cdp: false,
      cdp_url: "http://localhost:9222",
      wait_after_goto_ms: 3000,
      wait_after_detail_ms: 3000,
      random_delay_min: 1,
      random_delay_max: 3,
    };

    const form = reactive({
      name: "",
      site_url: "",
      enabled: true,
      note: "",
      selectors: { ...defaultSelectors },
      crawl_rules: { ...defaultRules },
    });

    async function load() {
      loading.value = true;
      try {
        const res = await api.listChannels();
        channels.value = res.data.items || [];
      } catch (e) {
        emit("toast", { type: "error", title: "加载失败", message: e.message });
      } finally {
        loading.value = false;
      }
    }

    function openCreate() {
      editingId.value = null;
      Object.assign(form, {
        name: "",
        site_url: "",
        enabled: true,
        note: "",
        selectors: { ...defaultSelectors },
        crawl_rules: { ...defaultRules },
      });
      showModal.value = true;
    }

    function openEdit(item) {
      editingId.value = item.id;
      Object.assign(form, {
        name: item.name,
        site_url: item.site_url,
        enabled: item.enabled,
        note: item.note || "",
        selectors: { ...defaultSelectors, ...(item.selectors || {}) },
        crawl_rules: { ...defaultRules, ...(item.crawl_rules || {}) },
      });
      showModal.value = true;
    }

    async function save() {
      const payload = {
        name: form.name,
        site_url: form.site_url,
        enabled: form.enabled,
        note: form.note,
        selectors: form.selectors,
        crawl_rules: form.crawl_rules,
      };
      try {
        if (editingId.value) {
          await api.updateChannel(editingId.value, payload);
          emit("toast", { type: "success", title: "更新成功", message: "渠道已保存" });
        } else {
          await api.createChannel(payload);
          emit("toast", { type: "success", title: "创建成功", message: "渠道已添加" });
        }
        showModal.value = false;
        await load();
      } catch (e) {
        emit("toast", { type: "error", title: "保存失败", message: e.message });
      }
    }

    async function remove(id) {
      if (!confirm("确定删除该渠道？关联的任务也会被删除。")) return;
      try {
        await api.deleteChannel(id);
        emit("toast", { type: "success", title: "删除成功" });
        await load();
      } catch (e) {
        emit("toast", { type: "error", title: "删除失败", message: e.message });
      }
    }

    onMounted(load);

    return { channels, loading, showModal, editingId, form, load, openCreate, openEdit, save, remove };
  },
  template: `
    <div>
      <div class="page-header">
        <h1>渠道管理</h1>
        <button class="btn-primary" @click="openCreate">+ 新增渠道</button>
      </div>

      <div class="card">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>站点URL</th>
              <th>状态</th>
              <th>创建时间</th>
              <th style="text-align:right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in channels" :key="c.id">
              <td>{{ c.id }}</td>
              <td>{{ c.name }}</td>
              <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis">{{ c.site_url }}</td>
              <td>
                <span class="badge" :class="c.enabled ? 'badge-success' : 'badge-idle'">
                  {{ c.enabled ? '启用' : '禁用' }}
                </span>
              </td>
              <td>{{ new Date(c.created_at).toLocaleString() }}</td>
              <td style="text-align:right">
                <button class="btn-secondary" style="margin-right:8px" @click="openEdit(c)">编辑</button>
                <button class="btn-danger" @click="remove(c.id)">删除</button>
              </td>
            </tr>
            <tr v-if="!loading && channels.length === 0">
              <td colspan="6" style="text-align:center;color:#9ca3af">暂无渠道，点击右上角新增</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ editingId ? '编辑渠道' : '新增渠道' }}</h3>
            <button class="btn-secondary" @click="showModal = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <div class="form-group">
                <label>渠道名称</label>
                <input v-model="form.name" placeholder="如：LinkedIn" />
              </div>
              <div class="form-group">
                <label>站点入口URL</label>
                <input v-model="form.site_url" placeholder="https://www.linkedin.com/jobs/search?..." />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>状态</label>
                <select v-model="form.enabled">
                  <option :value="true">启用</option>
                  <option :value="false">禁用</option>
                </select>
              </div>
              <div class="form-group">
                <label>备注</label>
                <input v-model="form.note" placeholder="可选" />
              </div>
            </div>

            <div class="section-title">列表页选择器</div>
            <div class="form-row three">
              <div class="form-group">
                <label>卡片容器</label>
                <input v-model="form.selectors.list_container" placeholder=".jobs-search__results-list" />
              </div>
              <div class="form-group">
                <label>职位卡片</label>
                <input v-model="form.selectors.job_card" placeholder=".job-card-container" />
              </div>
              <div class="form-group">
                <label>详情链接</label>
                <input v-model="form.selectors.detail_link" placeholder="a[href]" />
              </div>
            </div>
            <div class="form-row three">
              <div class="form-group"><label>标题</label><input v-model="form.selectors.title" /></div>
              <div class="form-group"><label>公司</label><input v-model="form.selectors.company" /></div>
              <div class="form-group"><label>地点</label><input v-model="form.selectors.location" /></div>
            </div>
            <div class="form-row three">
              <div class="form-group"><label>薪资</label><input v-model="form.selectors.salary" /></div>
              <div class="form-group"><label>描述</label><input v-model="form.selectors.description" /></div>
              <div class="form-group"><label>下一页</label><input v-model="form.selectors.next_page" /></div>
            </div>

            <div class="section-title">详情页选择器</div>
            <div class="form-row three">
              <div class="form-group"><label>标题</label><input v-model="form.selectors.detail_title" /></div>
              <div class="form-group"><label>公司</label><input v-model="form.selectors.detail_company" /></div>
              <div class="form-group"><label>地点</label><input v-model="form.selectors.detail_location" /></div>
            </div>
            <div class="form-row three">
              <div class="form-group"><label>薪资</label><input v-model="form.selectors.detail_salary" /></div>
              <div class="form-group"><label>描述</label><input v-model="form.selectors.detail_description" /></div>
              <div class="form-group"><label>弹窗关闭</label><input v-model="form.selectors.cookie_banner" /></div>
            </div>

            <div class="section-title">爬取规则</div>
            <div class="form-row three">
              <div class="form-group"><label>最大页数</label><input type="number" v-model.number="form.crawl_rules.max_pages" /></div>
              <div class="form-group"><label>最大岗位数</label><input type="number" v-model.number="form.crawl_rules.max_jobs" /></div>
              <div class="form-group"><label>滚动次数</label><input type="number" v-model.number="form.crawl_rules.scroll_times" /></div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>模式</label>
                <select v-model="form.crawl_rules.headless">
                  <option :value="true">无头模式 (headless)</option>
                  <option :value="false">可视化窗口</option>
                </select>
              </div>
              <div class="form-group">
                <label>CDP 连接</label>
                <select v-model="form.crawl_rules.use_cdp">
                  <option :value="false">启动新浏览器</option>
                  <option :value="true">连接 Chrome CDP</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group"><label>CDP 地址</label><input v-model="form.crawl_rules.cdp_url" placeholder="http://localhost:9222" /></div>
              <div class="form-group"><label>页面等待(ms)</label><input type="number" v-model.number="form.crawl_rules.wait_after_goto_ms" /></div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showModal = false">取消</button>
            <button class="btn-primary" @click="save">保存</button>
          </div>
        </div>
      </div>
    </div>
  `,
};

/* ==================== 任务控制面板 ==================== */
const TasksPage = {
  emits: ["toast"],
  setup(props, { emit }) {
    const tasks = ref([]);
    const channels = ref([]);
    const loading = ref(false);
    const showModal = ref(false);
    const showLogs = ref(false);
    const editingId = ref(null);
    const logs = ref([]);
    const logTaskName = ref("");
    const running = ref({});

    const form = reactive({
      name: "",
      channel_id: null,
      max_pages: 5,
      max_jobs: 200,
      use_cdp: false,
      cdp_url: "http://localhost:9222",
      headless: true,
      schedule: "",
    });

    async function load() {
      loading.value = true;
      try {
        const [tRes, cRes] = await Promise.all([api.listTasks(), api.listChannels()]);
        tasks.value = tRes.data.items || [];
        channels.value = cRes.data.items || [];
      } catch (e) {
        emit("toast", { type: "error", title: "加载失败", message: e.message });
      } finally {
        loading.value = false;
      }
    }

    function channelName(id) {
      const c = channels.value.find((x) => x.id === id);
      return c ? c.name : id;
    }

    function openCreate() {
      editingId.value = null;
      Object.assign(form, {
        name: "",
        channel_id: channels.value[0]?.id || null,
        max_pages: 5,
        max_jobs: 200,
        use_cdp: false,
        cdp_url: "http://localhost:9222",
        headless: true,
        schedule: "",
      });
      showModal.value = true;
    }

    function openEdit(item) {
      editingId.value = item.id;
      Object.assign(form, {
        name: item.name,
        channel_id: item.channel_id,
        max_pages: item.max_pages,
        max_jobs: item.max_jobs,
        use_cdp: item.use_cdp,
        cdp_url: item.cdp_url,
        headless: item.headless,
        schedule: item.schedule,
      });
      showModal.value = true;
    }

    async function save() {
      const payload = { ...form };
      try {
        if (editingId.value) {
          await api.updateTask(editingId.value, payload);
          emit("toast", { type: "success", title: "更新成功" });
        } else {
          await api.createTask(payload);
          emit("toast", { type: "success", title: "创建成功" });
        }
        showModal.value = false;
        await load();
      } catch (e) {
        emit("toast", { type: "error", title: "保存失败", message: e.message });
      }
    }

    async function remove(id) {
      if (!confirm("确定删除该任务？")) return;
      try {
        await api.deleteTask(id);
        emit("toast", { type: "success", title: "删除成功" });
        await load();
      } catch (e) {
        emit("toast", { type: "error", title: "删除失败", message: e.message });
      }
    }

    async function run(item) {
      running.value[item.id] = true;
      emit("toast", { type: "success", title: "开始运行", message: `任务「${item.name}」正在采集...` });
      try {
        const res = await api.runTask(item.id);
        const data = res.data || {};
        emit("toast", {
          type: data.status === "success" ? "success" : "error",
          title: data.status === "success" ? "采集完成" : "采集失败",
          message: data.message || `新增 ${data.saved || 0} 条`,
        });
        await load();
      } catch (e) {
        emit("toast", { type: "error", title: "运行失败", message: e.message });
      } finally {
        running.value[item.id] = false;
      }
    }

    async function viewLogs(item) {
      logTaskName.value = item.name;
      showLogs.value = true;
      try {
        const res = await api.listTaskLogs(item.id, 100);
        logs.value = (res.data.items || []).reverse();
      } catch (e) {
        emit("toast", { type: "error", title: "加载日志失败", message: e.message });
      }
    }

    onMounted(load);

    return {
      tasks, channels, loading, showModal, showLogs, editingId, form, logs, logTaskName, running,
      load, channelName, openCreate, openEdit, save, remove, run, viewLogs,
    };
  },
  template: `
    <div>
      <div class="page-header">
        <h1>采集任务控制面板</h1>
        <button class="btn-primary" @click="openCreate">+ 新建任务</button>
      </div>

      <div class="card">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>任务名称</th>
              <th>关联渠道</th>
              <th>状态</th>
              <th>最大页/岗位</th>
              <th>上次运行</th>
              <th style="text-align:right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.id">
              <td>{{ t.id }}</td>
              <td>{{ t.name }}</td>
              <td>{{ channelName(t.channel_id) }}</td>
              <td>
                <span class="badge" :class="'badge-' + t.status">{{ t.status }}</span>
              </td>
              <td>{{ t.max_pages }} / {{ t.max_jobs }}</td>
              <td>{{ t.last_run_at ? new Date(t.last_run_at).toLocaleString() : '-' }}</td>
              <td style="text-align:right">
                <button class="btn-success" style="margin-right:6px" :disabled="running[t.id] || t.status === 'running'" @click="run(t)">
                  <span v-if="running[t.id]" class="loading"></span>
                  <span v-else>▶ 运行</span>
                </button>
                <button class="btn-secondary" style="margin-right:6px" @click="viewLogs(t)">日志</button>
                <button class="btn-secondary" style="margin-right:6px" @click="openEdit(t)">编辑</button>
                <button class="btn-danger" @click="remove(t.id)">删除</button>
              </td>
            </tr>
            <tr v-if="!loading && tasks.length === 0">
              <td colspan="7" style="text-align:center;color:#9ca3af">暂无任务，点击右上角新建</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 新建/编辑任务 -->
      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal" style="max-width:520px">
          <div class="modal-header">
            <h3>{{ editingId ? '编辑任务' : '新建任务' }}</h3>
            <button class="btn-secondary" @click="showModal = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>任务名称</label>
              <input v-model="form.name" />
            </div>
            <div class="form-group">
              <label>关联渠道</label>
              <select v-model.number="form.channel_id">
                <option v-for="c in channels" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
            <div class="form-row">
              <div class="form-group"><label>最大页数</label><input type="number" v-model.number="form.max_pages" /></div>
              <div class="form-group"><label>最大岗位数</label><input type="number" v-model.number="form.max_jobs" /></div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>浏览器模式</label>
                <select v-model="form.headless">
                  <option :value="true">无头</option>
                  <option :value="false">可视化</option>
                </select>
              </div>
              <div class="form-group">
                <label>使用 CDP</label>
                <select v-model="form.use_cdp">
                  <option :value="false">启动新浏览器</option>
                  <option :value="true">连接本地 Chrome</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>CDP 地址</label>
              <input v-model="form.cdp_url" placeholder="http://localhost:9222" />
            </div>
            <div class="form-group">
              <label>定时规则 (Cron，可选)</label>
              <input v-model="form.schedule" placeholder="0 9 * * *" />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showModal = false">取消</button>
            <button class="btn-primary" @click="save">保存</button>
          </div>
        </div>
      </div>

      <!-- 日志弹窗 -->
      <div v-if="showLogs" class="modal-overlay" @click.self="showLogs = false">
        <div class="modal" style="max-width:640px">
          <div class="modal-header">
            <h3>运行日志 - {{ logTaskName }}</h3>
            <button class="btn-secondary" @click="showLogs = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="log-list">
              <div v-for="log in logs" :key="log.id" class="log-item" :class="log.level">
                [{{ new Date(log.created_at).toLocaleTimeString() }}] {{ log.message }}
              </div>
              <div v-if="logs.length === 0" style="color:#9ca3af">暂无日志</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
};

/* ==================== 岗位列表页 ==================== */
const JobsPage = {
  emits: ["toast"],
  setup(props, { emit }) {
    const jobs = ref([]);
    const stats = ref({ total: 0, standardized: 0, unstandardized: 0, task_count: 0 });
    const loading = ref(false);
    const filters = reactive({
      keyword: "",
      task_id: "",
      is_standardized: "",
      work_location_type: "",
    });
    const pagination = reactive({ page: 1, page_size: 15, total: 0 });
    const detailJob = ref(null);
    const tasks = ref([]);

    async function loadStats() {
      try {
        const res = await api.getJobStats();
        stats.value = res;
      } catch (e) {
        emit("toast", { type: "error", title: "统计失败", message: e.message });
      }
    }

    async function loadTasks() {
      try {
        const res = await api.listTasks({ limit: 100 });
        tasks.value = res.data.items || [];
      } catch (e) {
        console.error(e);
      }
    }

    async function loadJobs() {
      loading.value = true;
      try {
        const params = {
          page: pagination.page,
          page_size: pagination.page_size,
        };
        if (filters.keyword) params.keyword = filters.keyword;
        if (filters.task_id) params.task_id = Number(filters.task_id);
        if (filters.is_standardized !== "") params.is_standardized = filters.is_standardized === "true";
        if (filters.work_location_type) params.work_location_type = filters.work_location_type;
        const res = await api.listJobs(params);
        jobs.value = res.items || [];
        pagination.total = res.total || 0;
      } catch (e) {
        emit("toast", { type: "error", title: "加载失败", message: e.message });
      } finally {
        loading.value = false;
      }
    }

    async function standardize() {
      try {
        const params = filters.task_id ? { taskId: Number(filters.task_id) } : {};
        const res = await api.standardizeJobs(params.taskId);
        emit("toast", { type: "success", title: "标准化完成", message: `更新 ${res.stats.updated} 条` });
        await loadJobs();
        await loadStats();
      } catch (e) {
        emit("toast", { type: "error", title: "标准化失败", message: e.message });
      }
    }

    async function openDetail(job) {
      try {
        const res = await api.getJob(job.id);
        detailJob.value = res;
      } catch (e) {
        emit("toast", { type: "error", title: "加载详情失败", message: e.message });
      }
    }

    function resetFilters() {
      filters.keyword = "";
      filters.task_id = "";
      filters.is_standardized = "";
      filters.work_location_type = "";
      pagination.page = 1;
      loadJobs();
    }

    watch(() => ({ ...filters }), () => { pagination.page = 1; loadJobs(); }, { deep: true });

    onMounted(() => {
      loadJobs();
      loadStats();
      loadTasks();
    });

    return {
      jobs, stats, loading, filters, pagination, detailJob, tasks,
      loadJobs, standardize, openDetail, resetFilters,
    };
  },
  template: `
    <div>
      <div class="page-header">
        <h1>岗位列表</h1>
        <button class="btn-primary" @click="standardize">🔄 一键标准化</button>
      </div>

      <div class="stats-row">
        <div class="stat-card"><div class="stat-value">{{ stats.total }}</div><div class="stat-label">岗位总数</div></div>
        <div class="stat-card"><div class="stat-value">{{ stats.standardized }}</div><div class="stat-label">已标准化</div></div>
        <div class="stat-card"><div class="stat-value">{{ stats.unstandardized }}</div><div class="stat-label">未标准化</div></div>
        <div class="stat-card"><div class="stat-value">{{ stats.task_count }}</div><div class="stat-label">来源任务</div></div>
      </div>

      <div class="card filters">
        <input v-model="filters.keyword" placeholder="搜索标题/公司/描述" @keyup.enter="loadJobs" />
        <select v-model="filters.task_id">
          <option value="">全部任务</option>
          <option v-for="t in tasks" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <select v-model="filters.is_standardized">
          <option value="">全部状态</option>
          <option value="true">已标准化</option>
          <option value="false">未标准化</option>
        </select>
        <select v-model="filters.work_location_type">
          <option value="">全部工作方式</option>
          <option value="online_remote">线上远程</option>
          <option value="offline_office">线下办公</option>
        </select>
        <button class="btn-secondary" @click="resetFilters">重置</button>
      </div>

      <div class="card">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>职位</th>
              <th>公司</th>
              <th>地点</th>
              <th>薪资</th>
              <th>状态</th>
              <th>采集时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="j in jobs" :key="j.id">
              <td>{{ j.id }}</td>
              <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis">{{ j.title }}</td>
              <td>{{ j.company }}</td>
              <td>{{ j.location }}</td>
              <td>{{ j.salary }}</td>
              <td>
                <span class="badge" :class="j.is_standardized ? 'badge-success' : 'badge-idle'">
                  {{ j.is_standardized ? '已标准化' : '未标准化' }}
                </span>
              </td>
              <td>{{ new Date(j.created_at).toLocaleString() }}</td>
              <td>
                <button class="btn-secondary" @click="openDetail(j)">详情</button>
              </td>
            </tr>
            <tr v-if="!loading && jobs.length === 0">
              <td colspan="8" style="text-align:center;color:#9ca3af">暂无岗位数据，先去运行采集任务吧</td>
            </tr>
          </tbody>
        </table>

        <div class="pagination" v-if="pagination.total > 0">
          <button :disabled="pagination.page === 1" @click="pagination.page--; loadJobs()">上一页</button>
          <span>第 {{ pagination.page }} 页 / 共 {{ Math.ceil(pagination.total / pagination.page_size) }} 页</span>
          <button :disabled="pagination.page * pagination.page_size >= pagination.total" @click="pagination.page++; loadJobs()">下一页</button>
        </div>
      </div>

      <div v-if="detailJob" class="modal-overlay" @click.self="detailJob = null">
        <div class="modal" style="max-width:720px">
          <div class="modal-header">
            <h3>岗位详情</h3>
            <button class="btn-secondary" @click="detailJob = null">✕</button>
          </div>
          <div class="modal-body">
            <div class="detail-section">
              <div class="detail-title">{{ detailJob.title }}</div>
              <div class="detail-subtitle">{{ detailJob.company }} · {{ detailJob.location }}</div>
              <div class="detail-salary">{{ detailJob.salary }}</div>
            </div>
            <div class="detail-section">
              <h4>职位描述</h4>
              <div class="detail-desc">{{ detailJob.description }}</div>
            </div>
            <div class="detail-section" v-if="detailJob.matched_skills && detailJob.matched_skills.length">
              <h4>匹配技能</h4>
              <div class="skill-tags">
                <span v-for="(s, idx) in detailJob.matched_skills" :key="idx" class="skill-tag">
                  {{ s.primary }}{{ s.secondary ? ' / ' + s.secondary : '' }}
                </span>
              </div>
            </div>
            <div class="detail-section" v-if="detailJob.standardized_data">
              <h4>标准化数据</h4>
              <pre class="json-block">{{ JSON.stringify(detailJob.standardized_data, null, 2) }}</pre>
            </div>
            <div class="detail-section">
              <h4>来源链接</h4>
              <a :href="detailJob.url" target="_blank" class="link">{{ detailJob.url }}</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
};

/* ==================== Excel 导出页 ==================== */
const ExportPage = {
  emits: ["toast"],
  setup(props, { emit }) {
    const tasks = ref([]);
    const selectedTask = ref("");
    const standardizedOnly = ref(true);
    const exporting = ref(false);

    async function loadTasks() {
      try {
        const res = await api.listTasks({ limit: 100 });
        tasks.value = res.data.items || [];
      } catch (e) {
        emit("toast", { type: "error", title: "加载失败", message: e.message });
      }
    }

    async function exportExcel() {
      exporting.value = true;
      try {
        const blob = await api.exportExcel(
          selectedTask.value ? Number(selectedTask.value) : null,
          standardizedOnly.value
        );
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `jobs_export_${new Date().toISOString().slice(0,19).replace(/[-:T]/g,'')}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        emit("toast", { type: "success", title: "导出成功", message: "Excel 已开始下载" });
      } catch (e) {
        emit("toast", { type: "error", title: "导出失败", message: e.message });
      } finally {
        exporting.value = false;
      }
    }

    onMounted(loadTasks);

    return { tasks, selectedTask, standardizedOnly, exporting, exportExcel };
  },
  template: `
    <div>
      <div class="page-header">
        <h1>Excel 导出</h1>
      </div>
      <div class="card" style="max-width:560px">
        <div class="form-group">
          <label>选择任务（可选）</label>
          <select v-model="selectedTask">
            <option value="">全部任务</option>
            <option v-for="t in tasks" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="standardizedOnly" />
            仅导出已标准化数据
          </label>
        </div>
        <div class="form-info">
          导出文件包含两个 Sheet：<br/>
          1. <b>平台公司导入</b>：按公司名称去重；<br/>
          2. <b>任务导入</b>：每条岗位一行，字段严格对齐模板。
        </div>
        <button class="btn-primary" :disabled="exporting" @click="exportExcel" style="margin-top:16px">
          <span v-if="exporting" class="loading"></span>
          <span v-else>📥 一键导出 Excel</span>
        </button>
      </div>
    </div>
  `,
};

/* ==================== 根组件 ==================== */
const App = {
  setup() {
    const currentRoute = ref("channels");
    const isLoggedIn = ref(!!localStorage.getItem("token"));
    const currentUser = ref("admin");
    const toasts = ref([]);

    function navigate(route) {
      currentRoute.value = route;
      window.location.hash = route;
    }

    function handleLogin() {
      isLoggedIn.value = true;
      navigate("channels");
      validateToken();
    }

    function handleLogout() {
      localStorage.removeItem("token");
      isLoggedIn.value = false;
      currentUser.value = "";
      navigate("login");
    }

    async function validateToken() {
      try {
        const res = await api.me();
        currentUser.value = res.data.username || "admin";
      } catch {
        handleLogout();
      }
    }

    function toast({ type = "success", title, message = "" }) {
      const id = Date.now() + Math.random();
      toasts.value.push({ id, type, title, message });
      setTimeout(() => {
        toasts.value = toasts.value.filter((t) => t.id !== id);
      }, 3000);
    }

    onMounted(() => {
      const hash = window.location.hash.replace("#", "") || "channels";
      const valid = ["channels", "tasks", "jobs", "export"];
      currentRoute.value = valid.includes(hash) ? hash : "channels";
      if (isLoggedIn.value) validateToken();
    });

    return {
      currentRoute,
      isLoggedIn,
      currentUser,
      toasts,
      navigate,
      handleLogin,
      handleLogout,
      toast,
    };
  },
  template: `
    <div>
      <toast-container :toasts="toasts" />
      <login-page v-if="!isLoggedIn" @login="handleLogin" />
      <main-layout
        v-else
        :current-route="currentRoute"
        :current-user="currentUser"
        @navigate="navigate"
        @logout="handleLogout"
      >
        <channels-page v-if="currentRoute === 'channels'" @toast="toast" />
        <tasks-page v-if="currentRoute === 'tasks'" @toast="toast" />
        <jobs-page v-if="currentRoute === 'jobs'" @toast="toast" />
        <export-page v-if="currentRoute === 'export'" @toast="toast" />
      </main-layout>
    </div>
  `,
  components: {
    LoginPage,
    MainLayout,
    ChannelsPage,
    TasksPage,
    JobsPage,
    ExportPage,
    ToastContainer,
  },
};

createApp(App).mount("#app");
