import type { GeneratedPaper } from './generator'
import type { Question } from './types'

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function questionBlockHtml(q: Question, showAnswer: boolean, subLabel?: string): string {
  const prefix = subLabel ? `<strong>${escapeHtml(subLabel)}</strong> ` : ''
  let html = `<div class="q">${prefix}${escapeHtml(q.text).replace(/\n/g, '<br>')}</div>`
  if (q.options?.length) {
    html += '<ol type="a">'
    for (const opt of q.options) {
      html += `<li>${escapeHtml(opt)}</li>`
    }
    html += '</ol>'
  }
  if (q.orText) {
    html += `<p><strong>OR</strong><br>${escapeHtml(q.orText).replace(/\n/g, '<br>')}</p>`
  }
  if (showAnswer && q.answer) {
    html += `<p class="ans"><strong>Answer:</strong> ${escapeHtml(q.answer)}</p>`
  }
  return html
}

export function paperToHtml(paper: GeneratedPaper, showAnswers: boolean): string {
  const sections = paper.sections
    .map((sec) => {
      const items = sec.items
        .map((item) => {
          let body = ''
          if (item.passage) {
            body += `<div class="passage">${escapeHtml(item.passage).replace(/\n/g, '<br>')}</div>`
          }
          if (item.figureNote) {
            body += `<p class="note">${escapeHtml(item.figureNote)}</p>`
          }
          item.questions.forEach((q, idx) => {
            const sub =
              item.questions.length > 1 ? `(${idx + 1}) ` : undefined
            body += questionBlockHtml(q, showAnswers, sub)
          })
          return `<div class="item"><div class="qhead">Q.${item.number} <span class="marks">[${item.marks}]</span></div>${body}</div>`
        })
        .join('')
      return `<section><h2>${escapeHtml(sec.title)}</h2><p>${escapeHtml(sec.instruction)}</p>${items}</section>`
    })
    .join('')

  const gi = paper.generalInstructions.map((l) => `<li>${escapeHtml(l)}</li>`).join('')

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>${escapeHtml(paper.title)}</title>
<style>
  body { font-family: Georgia, serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; line-height: 1.45; color: #1c1915; }
  h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  .meta { color: #4a433a; margin-bottom: 1.5rem; }
  h2 { font-size: 1.1rem; margin-top: 1.5rem; border-bottom: 1px solid #d9cfc0; }
  .item { margin: 1rem 0 1.25rem; }
  .qhead { font-weight: bold; margin-bottom: 0.35rem; }
  .marks { font-weight: normal; color: #4a433a; }
  .passage { background: #f4efe6; padding: 0.6rem 0.75rem; margin-bottom: 0.5rem; font-size: 0.95rem; }
  .note { font-style: italic; color: #8a3b12; font-size: 0.9rem; }
  .ans { color: #0f5c4c; font-size: 0.95rem; }
  ol { margin: 0.35rem 0 0.5rem 1.25rem; }
  @media print { body { margin: 0; max-width: none; } }
</style>
</head>
<body>
<h1>${escapeHtml(paper.title)}</h1>
<p class="meta">${escapeHtml(paper.subtitle)}<br>
Time: ${escapeHtml(paper.time)} · Maximum marks: ${paper.maxMarks}</p>
<h2>General instructions</h2>
<ol>${gi}</ol>
${sections}
</body>
</html>`
}

export function paperToMarkdown(paper: GeneratedPaper, showAnswers: boolean): string {
  const lines: string[] = [
    `# ${paper.title}`,
    '',
    paper.subtitle,
    '',
    `**Time allowed:** ${paper.time}  ·  **Maximum marks:** ${paper.maxMarks}`,
    '',
    '## General instructions',
    '',
    ...paper.generalInstructions.map((l) => `- ${l}`),
    '',
  ]

  for (const sec of paper.sections) {
    lines.push(`## ${sec.title}`, '', sec.instruction, '')
    for (const item of sec.items) {
      lines.push(`### Q.${item.number} [${item.marks}]`, '')
      if (item.passage) {
        lines.push('> ' + item.passage.replace(/\n/g, '\n> '), '')
      }
      if (item.figureNote) {
        lines.push(`*${item.figureNote}*`, '')
      }
      item.questions.forEach((q, idx) => {
        if (item.questions.length > 1) lines.push(`**(${idx + 1})**`)
        lines.push(q.text, '')
        if (q.options?.length) {
          q.options.forEach((opt, i) => lines.push(`${String.fromCharCode(97 + i)}. ${opt}`))
          lines.push('')
        }
        if (q.orText) {
          lines.push('**OR**', '', q.orText, '')
        }
        if (showAnswers && q.answer) {
          lines.push(`**Answer:** ${q.answer}`, '')
        }
      })
    }
  }
  return lines.join('\n')
}

function downloadBlob(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function downloadPaperHtml(paper: GeneratedPaper, showAnswers: boolean) {
  const slug = paper.generatedAt.slice(0, 10)
  downloadBlob(
    `chemcompass-paper-${slug}.html`,
    paperToHtml(paper, showAnswers),
    'text/html;charset=utf-8',
  )
}

export function downloadPaperMarkdown(paper: GeneratedPaper, showAnswers: boolean) {
  const slug = paper.generatedAt.slice(0, 10)
  downloadBlob(
    `chemcompass-paper-${slug}.md`,
    paperToMarkdown(paper, showAnswers),
    'text/markdown;charset=utf-8',
  )
}
