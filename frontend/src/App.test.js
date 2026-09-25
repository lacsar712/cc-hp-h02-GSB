import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import App from './App.svelte'

const ROWS = [
  { id: 2, herb: '黄芩', doc: { steps: [{ name: '清炒', temp_c: 40, minutes: 12 }] }, verdict: '未放行', reason: '清炒温度不在范围内', created_by: 'processor' },
  { id: 1, herb: '甘草', doc: { steps: [{ name: '清炒', temp_c: 120, minutes: 12 }] }, verdict: '放行', reason: '清炒工序符合炮制要求', created_by: 'processor' },
]

// postStatus 改成 403 可模拟接口拒写
const mockState = { postStatus: 201 }

function respond(data, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => data }
}

function mockFetch(path, options = {}) {
  const auth = options.headers?.Authorization || ''
  const isWriter = auth.includes('processor')
  if (path === '/api/auth/login') {
    const { username } = JSON.parse(options.body)
    return respond({ access_token: `token-${username}`, username, role: username === 'processor' ? 'writer' : 'reader' })
  }
  if (path === '/api/auth/form-flag') return respond({ show_form: isWriter })
  if (path === '/api/batches' && !options.method) return respond(ROWS)
  if (path === '/api/batches' && options.method === 'POST') {
    if (!isWriter || mockState.postStatus !== 201) return respond({ detail: '仅炮制员可写入记录' }, 403)
    const body = JSON.parse(options.body)
    return respond({ id: 3, herb: body.herb, doc: { steps: body.steps }, verdict: '放行', reason: '清炒工序符合炮制要求', created_by: 'processor' }, 201)
  }
  throw new Error(`未预期的请求: ${path}`)
}

const listCalls = () =>
  vi.mocked(fetch).mock.calls.filter(([path, options]) => path === '/api/batches' && !options?.method).length

async function loginAs(container, username, password) {
  const [userInput, passInput] = container.querySelectorAll('input')
  await fireEvent.input(userInput, { target: { value: username } })
  await fireEvent.input(passInput, { target: { value: password } })
  await fireEvent.click(screen.getByText('登录'))
  await screen.findByText('甘草 · 放行 · 清炒工序符合炮制要求 · 温度 120')
}

beforeEach(() => {
  localStorage.clear()
  mockState.postStatus = 201
  vi.stubGlobal('fetch', vi.fn(mockFetch))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('首页渲染越权', () => {
  it('质检登录后首页无表单', async () => {
    const { container } = render(App)
    await loginAs(container, 'checker', 'check123456')
    expect(screen.queryByText('写入清炒记录')).toBeNull()
    expect(container.querySelectorAll('input').length).toBe(0)
  })

  it('带 token 重进（原偶发路径）质检仍无表单', async () => {
    localStorage.setItem('herb_token', 'token-checker')
    localStorage.setItem('herb_role', 'reader')
    const { container } = render(App)
    await screen.findByText('甘草 · 放行 · 清炒工序符合炮制要求 · 温度 120')
    expect(screen.queryByText('写入清炒记录')).toBeNull()
    expect(container.querySelectorAll('input').length).toBe(0)
  })

  it('炮制员登录后看到表单', async () => {
    const { container } = render(App)
    await loginAs(container, 'processor', 'herb123456')
    expect(screen.getByText('写入清炒记录')).toBeTruthy()
    expect(container.querySelectorAll('input').length).toBe(3)
  })
})

describe('列表刷新越权', () => {
  it('炮制员提交够线清炒成功后刷新列表', async () => {
    const { container } = render(App)
    await loginAs(container, 'processor', 'herb123456')
    expect(listCalls()).toBe(1)
    await fireEvent.click(screen.getByText('写入清炒记录'))
    await waitFor(() => expect(listCalls()).toBe(2))
    const post = vi.mocked(fetch).mock.calls.find(([path, options]) => path === '/api/batches' && options?.method === 'POST')
    expect(JSON.parse(post[1].body)).toEqual({ herb: '白芍', steps: [{ name: '清炒', temp_c: 110, minutes: 10 }] })
  })

  it('写入被拒后不再刷新列表', async () => {
    mockState.postStatus = 403
    const { container } = render(App)
    await loginAs(container, 'processor', 'herb123456')
    expect(listCalls()).toBe(1)
    await fireEvent.click(screen.getByText('写入清炒记录'))
    await screen.findByText('仅炮制员可写入记录')
    expect(listCalls()).toBe(1)
  })
})
