import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

// shape of a single chat message held in React state
interface Message {
  role: 'user' | 'assistant'
  content: string
  toolCalls: string[]  // names of Strava tools the agent called while generating this message
}

// new session ID on every page load — each visit starts a fresh conversation
const sessionId = crypto.randomUUID()

function App() {
  const [messages, setMessages] = useState<Message[]>([])  // full conversation shown in the UI
  const [input, setInput] = useState('')                    // current value of the text input
  const [loading, setLoading] = useState(false)             // true while waiting for a response
  const bottomRef = useRef<HTMLDivElement>(null)            // invisible div at the bottom of the message list

  // scroll to the bottom whenever messages change (new message or streaming content added)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setLoading(true)

    // add the user message and an empty assistant message to the UI immediately
    setMessages(prev => [...prev, { role: 'user', content: text, toolCalls: [] }])
    setMessages(prev => [...prev, { role: 'assistant', content: '', toolCalls: [] }])

    const res = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    })

    // read the response as a stream of SSE events instead of waiting for the full response
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''  // incomplete line buffer — a chunk may arrive mid-line

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''  // keep the last incomplete line in the buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = JSON.parse(line.slice(6))

        if (data.type === 'text') {
          // append the token to the last message (the assistant's bubble being streamed)
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { ...next[next.length - 1], content: next[next.length - 1].content + data.delta }
            return next
          })
        } else if (data.type === 'tool_call') {
          // record which Strava tool the agent called so we can show it under the bubble
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
    // reset conversation history in the DB and clear the UI
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
            {/* show which tools were called above the assistant bubble */}
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
                  ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>  // render markdown for assistant
                  : loading && i === messages.length - 1
                    ? <span className="typing">···</span>  // show typing indicator while first tokens arrive
                    : null
                : msg.content}  {/* user messages are plain text */}
            </div>
          </div>
        ))}
        {/* invisible anchor that we scroll to on each update */}
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
