<script setup>
import { loginUrl } from '../api/client'

function go(asAdmin = false) {
  window.location.assign(loginUrl(asAdmin))
}

const features = [
  {
    title: '多轮追问',
    description: '围绕同一个业务问题持续深入，上下文不丢失。',
  },
  {
    title: '证据可追溯',
    description: '查询结果与文本证据逐条对应，结论有据可查。',
  },
  {
    title: '结构化交付',
    description: '关键指标、归因结论、待补充数据与下一步建议一次生成。',
  },
]
</script>

<template>
  <div class="auth-shell">
    <section class="auth-brand">
      <div class="auth-brand-glow"></div>
      <div class="auth-brand-grid"></div>

      <header class="auth-brand-head">
        <span class="brand-mark">归因</span>
        <div>
          <strong>经营归因分析系统</strong>
          <small>BUSINESS ATTRIBUTION</small>
        </div>
      </header>

      <div class="auth-brand-main">
        <p class="eyebrow">经营分析工作台</p>
        <h1>把业务问题，<br />变成可追溯的结论。</h1>
        <p class="lede">
          围绕一个业务问题持续追问，让数据、证据与结论在同一条链路上完成。
        </p>

        <ul class="feature-list">
          <li v-for="(feature, index) in features" :key="feature.title">
            <span class="feature-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <div>
              <strong>{{ feature.title }}</strong>
              <p>{{ feature.description }}</p>
            </div>
          </li>
        </ul>
      </div>

      <footer class="auth-brand-foot">
        <span class="status-dot"></span>
        让经营分析有据可查
      </footer>
    </section>

    <section class="auth-form-panel">
      <div class="auth-form-card">
        <div class="form-heading">
          <p class="eyebrow">欢迎回来</p>
          <h2>登录工作台</h2>
          <p>选择入口开始本次经营分析。</p>
        </div>

        <div class="auth-actions">
          <button class="btn primary auth-btn" @click="go(false)">登录</button>
          <button class="btn ghost auth-btn" @click="go(true)">管理员登录</button>
        </div>

        <p class="auth-footnote">管理员入口用于系统配置、日志与数据源查看。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth-shell {
  min-height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(380px, 0.85fr);
  background: var(--bg);
}

.auth-brand {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 36px;
  padding: 48px 56px;
  color: #fff;
  background:
    linear-gradient(145deg, #080f1d 0%, #0f1b31 52%, #16224a 100%);
}

.auth-brand-glow {
  position: absolute;
  width: 560px;
  height: 560px;
  top: -220px;
  right: -160px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.5), transparent 66%);
  pointer-events: none;
}

.auth-brand-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.85), transparent 78%);
  pointer-events: none;
}

.auth-brand-head,
.auth-brand-main,
.auth-brand-foot {
  position: relative;
  z-index: 1;
}

.auth-brand-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-brand-head strong {
  display: block;
  color: #fff;
  font-size: 15px;
  letter-spacing: 0.01em;
}

.auth-brand-head small {
  display: block;
  margin-top: 2px;
  color: #8ea6c7;
  font-size: 9px;
  letter-spacing: 0.18em;
}

.auth-brand-main {
  max-width: 600px;
}

.eyebrow {
  margin: 0 0 14px;
  color: #7dd3fc;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.auth-brand h1 {
  margin: 0;
  color: #f8fafc;
  font-size: clamp(34px, 3.4vw, 48px);
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: -0.03em;
}

.lede {
  max-width: 480px;
  margin: 20px 0 0;
  color: #a9b8ce;
  font-size: 15px;
  line-height: 1.8;
}

.feature-list {
  display: grid;
  gap: 18px;
  max-width: 500px;
  margin: 40px 0 0;
  padding: 0;
  list-style: none;
}

.feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.feature-index {
  display: grid;
  place-items: center;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(147, 197, 253, 0.28);
  border-radius: 50%;
  color: #93c5fd;
  font-family: var(--mono);
  font-size: 10px;
}

.feature-list strong {
  display: block;
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 700;
}

.feature-list p {
  margin: 4px 0 0;
  color: #8fa3bd;
  font-size: 12px;
  line-height: 1.6;
}

.auth-brand-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #7f93ac;
  font-size: 11px;
  letter-spacing: 0.04em;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.12);
}

.auth-form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: var(--bg);
}

.auth-form-card {
  width: min(380px, 100%);
}

.form-heading .eyebrow {
  margin-bottom: 10px;
  color: var(--accent);
}

.form-heading h2 {
  margin: 0;
  color: var(--ink);
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.form-heading p:last-child {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}

.auth-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 30px;
}

.auth-btn {
  width: 100%;
  height: 48px;
  font-size: 14px;
}

.auth-footnote {
  margin: 22px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 980px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-brand {
    min-height: 320px;
    padding: 32px;
  }

  .auth-brand-main {
    margin: 20px 0;
  }

  .feature-list {
    display: none;
  }

  .auth-form-panel {
    padding: 48px 28px 64px;
  }
}

@media (max-width: 560px) {
  .auth-brand {
    min-height: 250px;
    padding: 24px;
  }

  .auth-brand h1 {
    font-size: 30px;
  }

  .lede {
    font-size: 13px;
  }

  .auth-form-panel {
    padding: 36px 22px 48px;
  }
}
</style>
