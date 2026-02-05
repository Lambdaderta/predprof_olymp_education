// src/components/MarkdownRenderer.jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const MarkdownRenderer = ({ content, className = "" }) => {
  return (
    <div className={`prose max-w-none dark:prose-invert prose-indigo ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          a: ({ node, ...props }) => (
            <a
              {...props}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-500"
            />
          ),
          code: ({ node, inline, className, children, ...props }) => {
            return !inline ? (
              <div className="mockup-code bg-gray-900 text-gray-100 rounded-lg p-4 my-4 overflow-x-auto">
                <code {...props}>{children}</code>
              </div>
            ) : (
              <code
                className="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            );
          },
          // Исправляем стили для параграфов, чтобы формулы не ломали верстку
          p: ({ node, ...props }) => <p className="mb-4 leading-relaxed" {...props} />,
          // Картинки делаем адаптивными
          img: ({ node, ...props }) => (
            <img {...props} className="rounded-xl shadow-lg max-h-96 mx-auto" alt={props.alt || "image"} />
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;