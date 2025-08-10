// src/ChatPage.jsx

import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Box, Paper, Typography, TextField, IconButton } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

const socket = io('http://localhost:3001');

const ChatInputForm = ({ onSubmit, value, onChange }) => (
  <Box component="form" onSubmit={onSubmit} className="message-form-container">
    <TextField fullWidth variant="outlined" placeholder="Ask the agent anything..." value={value} onChange={onChange} autoComplete="off" autoFocus />
    <IconButton type="submit" color="primary" aria-label="send message" disabled={!value.trim()}>
      <SendIcon />
    </IconButton>
  </Box>
);

function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  useEffect(() => {
    const handleResponseChunk = (chunk) => {
      setIsTyping(true);
      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.sender === 'agent') {
          return [ ...prev.slice(0, -1), { ...lastMessage, text: lastMessage.text + chunk }, ];
        } else {
          return [...prev, { text: chunk, sender: 'agent' }];
        }
      });
    };
    const handleResponseEnd = () => setIsTyping(false);
    socket.on('agentResponseChunk', handleResponseChunk);
    socket.on('agentResponseEnd', handleResponseEnd);
    return () => {
      socket.off('agentResponseChunk', handleResponseChunk);
      socket.off('agentResponseEnd', handleResponseEnd);
    };
  }, []);

  const sendMessage = (e) => {
    e.preventDefault();
    if (input.trim()) {
      setMessages((prev) => [...prev, { text: input, sender: 'user' }]);
      socket.emit('sendMessage', input);
      setInput('');
      setIsTyping(true);
    }
  };

  if (messages.length === 0 && !isTyping) {
    return (
      <Box className="collapsed-view">
        <ChatInputForm onSubmit={sendMessage} value={input} onChange={(e) => setInput(e.target.value)} />
      </Box>
    );
  }

  return (
    <Box component="main" className="chat-window-container">
      <Paper elevation={3} className="chat-paper">
        <Box className="message-list">
          {messages.map((msg, index) => (
            <Box key={index} className={`message-bubble ${msg.sender}`}>
              {msg.sender === 'agent' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
              ) : (
                <Typography variant="body1">{msg.text}</Typography>
              )}
            </Box>
          ))}
          {isTyping && (
            <Box className="message-bubble agent">
              <Typography variant="body1" className="typing-indicator">...</Typography>
            </Box>
          )}
          <div ref={scrollRef} />
        </Box>
        <ChatInputForm onSubmit={sendMessage} value={input} onChange={(e) => setInput(e.target.value)} />
      </Paper>
    </Box>
  );
}

export default ChatPage;