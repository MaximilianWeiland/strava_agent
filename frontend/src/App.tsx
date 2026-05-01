import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolCalls: string[]
}

function getSessionId(): string {
  let id = localStorage.getItem('session_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('session_id', id)
  }
  return id
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const sessionId = getSessionId()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setLoading(true)

    setMessages(prev => [...prev, { role: 'user', content: text, toolCalls: [] }])
    setMessages(prev => [...prev, { role: 'assistant', content: '', toolCalls: [] }])

    const res = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    })

    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = JSON.parse(line.slice(6))
        if (data.type === 'text') {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], content: next[next.length - 1].content + data.delta }
            return next
          })
        } else if (data.type === 'tool_call') {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], toolCalls: [...next[next.length - 1].toolCalls, data.name] }
            return next
          })
        }
      }
    }

    setLoading(false)
  }

  const clear = async () => {
    await fetch(`http://localhost:8000/chat/${sessionId}`, { method: 'DELETE' })
    setMessages([])
  }

  return (
    <div className="app">
      <header>
        <div className="logo">
          <span className="logo-icon">S</span>
          <span>Strava Agent</span>
        </div>
        <button onClick={clear} className="clear-btn">Clear</button>
      </header>

      <div className="messages">
        {messages.length === 0 && (
          <p className="empty">Ask anything about your Strava data</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.toolCalls.length > 0 && (
              <div className="tool-calls">
                {msg.toolCalls.map((tc, j) => (
                  <span key={j} className="tool-call">↳ {tc}</span>
                ))}
              </div>
            )}
            <div className="bubble">
              {msg.role === 'assistant'
                ? msg.content
                  ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  : loading && i === messages.length - 1
                    ? <span className="typing">···</span>
                    : null
                : msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="input-bar">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Ask about your activities..."
          disabled={loading}
          autoFocus
        />
        <button onClick={send} disabled={loading || !input.trim()}>↑</button>
      </div>
    </div>
  )
}

export default App
