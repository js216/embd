#!/usr/bin/env python3
import sys
import re
import html
import hashlib
from pathlib import Path

# --- SYNTAX HIGHLIGHTING ---

def highlight_c(code):
    rules = [
        ('cp', r'#\w+'),
        ('c1', r'//.*'),
        ('cm', r'/\*[\s\S]*?\*/'),
        ('s',  r'"(?:\\.|[^"\\])*"'),
        ('m',  r'\b0x[0-9a-fA-F]+\b|\b\d+\b'),
        ('k',  r'\b(?:int|char|void|if|else|while|for|return|struct|static|extern|switch|case|break|continue|typedef|const|unsigned|long|short|default)\b'),
        ('nf', r'\b\w+(?=\s*\()'),
        ('o',  r'[=+\-*/%&|^!<>?]'),
    ]
    master_re = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in rules))

    def replace(match):
        for name, value in match.groupdict().items():
            if value: return f'<span class="{name}">{html.escape(value)}</span>'
        return html.escape(match.group(0))

    parts = []
    last_pos = 0
    for match in master_re.finditer(code):
        parts.append(html.escape(code[last_pos:match.start()]))
        parts.append(replace(match))
        last_pos = match.end()
    parts.append(html.escape(code[last_pos:]))
    return "".join(parts)

def highlight_python(code):
    rules = [
        ('c1', r'#.*'),                                       # Comments
        # Combined string patterns into one 's' group
        ('s',  r'"{3}[\s\S]*?"{3}|\'{3}[\s\S]*?\'{3}|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''),
        ('cp', r'@\w+'),                                      # Decorators
        ('k',  r'\b(?:def|class|if|elif|else|while|for|return|import|from|as|try|except|finally|with|lambda|yield|pass|break|continue|in|is|not|and|or|True|False|None|global|nonlocal|assert|del|raise)\b'),
        ('nf', r'\b\w+(?=\s*\()'),                            # Function calls
        ('m',  r'\b\d+\b|\b0x[0-9a-fA-F]+\b'),                # Numbers
        ('o',  r'[=+\-*/%&|^!<>~]'),                          # Operators
    ]
    master_re = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in rules))

    def replace(match):
        for name, value in match.groupdict().items():
            if value: return f'<span class="{name}">{html.escape(value)}</span>'
        return html.escape(match.group(0))

    parts = []
    last_pos = 0
    for match in master_re.finditer(code):
        parts.append(html.escape(code[last_pos:match.start()]))
        parts.append(replace(match))
        last_pos = match.end()
    parts.append(html.escape(code[last_pos:]))
    return "".join(parts)


# --- BLOCK PARSERS ---

def render_indented_code_blocks(text):
    lines = text.split('\n')
    result, buffer = [], []
    for line in lines:
        if (line.startswith('    ') or line.startswith('\t')) and (line.strip() or buffer):
            buffer.append(html.escape(line[4:] if line.startswith('    ') else line[1:]))
        else:
            if buffer:
                while buffer and not buffer[-1].strip(): buffer.pop()
                c_str = "\n".join(buffer)
                result.append(f'<pre><code>{c_str}</code></pre>')
                buffer = []
            result.append(line)
    if buffer:
        c_str = "\n".join(buffer)
        result.append(f'<pre><code>{c_str}</code></pre>')
    return '\n'.join(result)

def render_blockquotes(text):
    """Handles multi-paragraph blockquotes by identifying the '>' block."""
    lines = text.split('\n')
    result, buffer = [], []
    
    for line in lines:
        if line.lstrip().startswith('>'):
            # Strip the '>' and leading space
            content = re.sub(r'^\s*>\s?', '', line)
            buffer.append(content)
        else:
            if buffer:
                # Process the inner content as markdown to handle paragraphs
                inner_text = '\n'.join(buffer)
                # We wrap the internal text in paragraphs but exclude the <blockquote> tag itself
                inner_html = wrap_loose_paragraphs(inner_text)
                result.append(f'<blockquote>{inner_html}</blockquote>')
                buffer = []
            result.append(line)
    if buffer:
        inner_html = wrap_loose_paragraphs('\n'.join(buffer))
        result.append(f'<blockquote>{inner_html}</blockquote>')
    return '\n'.join(result)

def render_tables(text):
    lines = text.split('\n')
    output, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        # Look ahead for the separator line
        if (line.startswith('|') or '|' in line) and i + 1 < len(lines):
            sep_line = lines[i+1].strip()
            if re.match(r'^\|?[\s|:-]+\|?$', sep_line) and '|' in sep_line:
                # 1. Parse alignment from the separator row
                sep_parts = [s.strip() for s in sep_line.strip('|').split('|')]
                alignments = []
                for s in sep_parts:
                    if s.startswith(':') and s.endswith(':'):
                        alignments.append('center')
                    elif s.endswith(':'):
                        alignments.append('right')
                    else:
                        alignments.append('left')
                
                # 2. Parse header
                header_line = line.strip('|')
                headers = [h.strip() for h in header_line.split('|')]
                num_cols = len(headers)
                
                # Ensure alignments list matches column count
                while len(alignments) < num_cols:
                    alignments.append('left')

                table = ['<table><thead><tr>']
                for idx, h in enumerate(headers):
                    style = f' style="text-align:{alignments[idx]}"'
                    table.append(f'<th{style}>{render_inline(h)}</th>')
                table.append('</tr></thead><tbody>')
                i += 2
                
                # 3. Parse body rows
                while i < len(lines) and '|' in lines[i]:
                    row_line = lines[i].strip().strip('|')
                    cells = [c.strip() for c in row_line.split('|')]
                    
                    # Pad or truncate cells to match header count
                    cells = (cells + [''] * num_cols)[:num_cols]
                    
                    row_html = []
                    for idx, c in enumerate(cells):
                        style = f' style="text-align:{alignments[idx]}"'
                        row_html.append(f'<td{style}>{render_inline(c)}</td>')
                    
                    table.append(f'<tr>{"".join(row_html)}</tr>')
                    i += 1
                    
                table.append('</tbody></table>')
                output.append('\n'.join(table))
                continue
        
        output.append(lines[i])
        i += 1
    return '\n'.join(output)

def render_lists(text):
    lines = text.split('\n')
    output, i = [], 0
    
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\s*)(\d+\.|[*+-])\s+(.*)', line)
        
        if m:
            indent_str, marker, first_line = m.groups()
            indent_len = len(indent_str)
            tag = 'ol' if marker[0].isdigit() else 'ul'
            items, current_item = [], [first_line]
            i += 1
            
            while i < len(lines):
                is_indented = lines[i].startswith(indent_str + " ") or lines[i].startswith(indent_str + "\t")
                is_blank = lines[i].strip() == ""
                
                if is_indented or is_blank:
                    # Strip the list's base indentation for inner rendering
                    trimmed = lines[i][indent_len:]
                    if trimmed.startswith("    "): trimmed = trimmed[4:]
                    elif trimmed.startswith("\t"): trimmed = trimmed[1:]
                    current_item.append(trimmed)
                    i += 1
                elif re.match(r'^' + indent_str + r'(\d+\.|[*+-])\s+(.*)', lines[i]):
                    items.append('\n'.join(current_item))
                    next_m = re.match(r'^' + indent_str + r'(\d+\.|[*+-])\s+(.*)', lines[i])
                    current_item = [next_m.group(2)]
                    i += 1
                else: break
            
            items.append('\n'.join(current_item))
            res = [f'<{tag}>']
            for item in items:
                # Recursively wrap the content inside the LI
                res.append(f'<li>{wrap_loose_paragraphs(item)}</li>')
            res.append(f'</{tag}>')
            output.append('\n'.join(res))
        else:
            output.append(line); i += 1
    return '\n'.join(output)

# --- SMART QUOTES ---

def smartquotes(text):
    """Convert straight quotes to curly quotes."""
    # Protect code blocks and inline code from quote conversion
    # We'll use placeholders to mark these regions
    
    # Track code blocks and inline code
    protected = []
    placeholder_template = "\x00PROTECTED_{}\x00"
    
    def protect(match):
        idx = len(protected)
        protected.append(match.group(0))
        return placeholder_template.format(idx)
    
    # Protect fenced code blocks
    text = re.sub(r'<div class="codehilite">.*?</div>', protect, text, flags=re.DOTALL)
    # Protect pre/code blocks
    text = re.sub(r'<pre>.*?</pre>', protect, text, flags=re.DOTALL)
    # Protect inline code
    text = re.sub(r'<code>.*?</code>', protect, text, flags=re.DOTALL)
    
    # Apply smart quote rules
    # Opening double quote after whitespace or start of line
    text = re.sub(r'(^|[\s\(\[\{])"', r'\1"', text)
    # Closing double quote
    text = re.sub(r'"', r'"', text)
    
    # Opening single quote after whitespace or start of line
    text = re.sub(r"(^|[\s\(\[\{])'", r"\1'", text)
    # Closing single quote (also handles apostrophes)
    text = re.sub(r"'", r"'", text)
    
    # Restore protected regions
    for idx, original in enumerate(protected):
        text = text.replace(placeholder_template.format(idx), original)
    
    return text

# --- CORE PARSER ---

def wrap_loose_paragraphs(text):
    blocks = re.split(r'\n\n+', text.strip())
    processed = []
    for b in blocks:
        t = b.strip()
        if not t: continue
        # Prevent wrapping code blocks or other lists in <p>
        if re.match(r'<(div|table|h\d|pre|ol|ul|li|blockquote)|\x00FENCEDCODE', t):
            processed.append(t)
        else:
            processed.append(f'<p>{render_inline(t)}</p>')
    return '\n'.join(processed)

def render_inline(text):
    """Processes links and emphasis while protecting HTML attributes."""
    # 1. First, convert Markdown links/images to HTML
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # 2. Protect ALL HTML tags from the emphasis parser
    # This prevents underscores in URLs from being turned into <em> tags
    tags = []
    def protect_tag(m):
        idx = len(tags)
        tags.append(m.group(0))
        return f"\x00TAG{idx}\x00"
    
    # Temporarily hide anything inside < >
    text = re.sub(r'<[^>]+>', protect_tag, text)

    # 3. Apply Bold and Italic only to the remaining "safe" text
    # Bold italic
    text = re.sub(r'\*\*\*([\s\S]*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'___([\s\S]*?)___', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*([\s\S]*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__([\s\S]*?)__', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*([\s\S]*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_([\s\S]*?)_', r'<em>\1</em>', text)

    # 4. Restore the protected HTML tags
    for i, tag in enumerate(tags):
        text = text.replace(f"\x00TAG{i}\x00", tag)
        
    return text

def simple_markdown_parser(md_text):
    # 0. Extract footnotes FIRST
    footnotes = []
    lines = md_text.split('\n')
    filtered_lines = []
    i = 0
    
    while i < len(lines):
        match = re.match(r'^\[\^([^\]]+)\]:\s*(.*)', lines[i])
        if match:
            fn_id = match.group(1)
            content_lines = [match.group(2)]
            i += 1
            while i < len(lines) and lines[i] and lines[i][0] in ' \t':
                content_lines.append(lines[i].strip())
                i += 1
            content = ' '.join(content_lines).strip()
            footnotes.append((fn_id, content))
        else:
            filtered_lines.append(lines[i])
            i += 1
    
    md_text = '\n'.join(filtered_lines)
    
    # 1. Blocks
    protected_blocks = []
    placeholder_template = "\x00FENCEDCODE{}\x00"
    
    def replace_code_block(m):
        lang = m.group(1).lower() if m.group(1) else "text"
        code = m.group(2)
        if lang == "c":
            highlighted = highlight_c(code)
        elif lang == "python" or lang == "py":
            highlighted = highlight_python(code)
        else:
            highlighted = html.escape(code)
        result = f'<div class="codehilite"><pre><code class="language-{lang}">{highlighted}</code></pre></div>'
        idx = len(protected_blocks)
        protected_blocks.append(result)
        return placeholder_template.format(idx)

    md_text = re.sub(
        r'^(?P<indent>[ \t]*)```(?P<lang>\w*)[ \t]*\n(?P<code>.*?)\n(?P=indent)```[ \t]*$', 
        replace_code_block, 
        md_text, 
        flags=re.MULTILINE | re.DOTALL
    )
    md_text = render_indented_code_blocks(md_text)
    md_text = render_blockquotes(md_text)
    md_text = render_lists(md_text)
    md_text = render_tables(md_text)

    # 2. Protect inline code
    protected_inline_code = []
    inline_code_placeholder = "\x00INLINECODE{}\x00"
    
    def protect_inline_code(m):
        idx = len(protected_inline_code)
        protected_inline_code.append(f'<code>{html.escape(m.group(1))}</code>')
        return inline_code_placeholder.format(idx)
    
    md_text = re.sub(r'`([^`]+)`', protect_inline_code, md_text)

    # 3. Process links and emphasis using the new "tag-safe" helper
    md_text = render_inline(md_text)

    # 5. Restore inline code
    for idx, code in enumerate(protected_inline_code):
        md_text = md_text.replace(inline_code_placeholder.format(idx), code)

    # 6. Headers
    def h_repl(m):
        lvl = len(m.group(1)); txt = m.group(2).strip()
        hid = re.sub(r'[^\w\-]', '', txt.lower().replace(' ', '-'))
        return f'<h{lvl} id="{hid}">{txt}</h{lvl}>'
    md_text = re.sub(r'^(#{1,6})\s+(.*)$', h_repl, md_text, flags=re.MULTILINE)

    # 7. Final Paragraph Wrapping
    md_text = wrap_loose_paragraphs(md_text)
    
    # 8. Restore protected fenced code blocks
    for idx, original in enumerate(protected_blocks):
        md_text = md_text.replace(placeholder_template.format(idx), original)

    # 9. Process footnote references and add footnote section
    if footnotes:
        fn_id_to_num = {fn_id: str(i + 1) for i, (fn_id, _) in enumerate(footnotes)}
        
        def replace_ref(match):
            fn_id = match.group(1)
            num = fn_id_to_num.get(fn_id, fn_id)
            return f'<sup class="footnote-ref"><a href="#fn-{fn_id}" id="fnref-{fn_id}">[{num}]</a></sup>'
        md_text = re.sub(r'\[\^([^\]]+)\]', replace_ref, md_text)
        
        items = []
        for i, (fid, c) in enumerate(footnotes):
            num = i + 1
            # Apply the tag-safe inline renderer to the footnote content
            fn_content = render_inline(c)
            items.append(f'<li id="fn-{fid}" value="{num}">{fn_content} <a href="#fnref-{fid}">↩</a></li>')
        md_text += f'\n<hr><section class="footnotes"><ol>{"".join(items)}</ol></section>'

    return md_text

def main():
    if len(sys.argv) != 4: return print("Usage: md2html.py in.md temp.html out.html")
    md_path, temp_path, out_path = map(Path, sys.argv[1:])
    raw_text = md_path.read_text(encoding="utf-8")
    
    meta = {}
    body = raw_text
    if raw_text.startswith('---'):
        parts = re.split(r'^---\s*$', raw_text, maxsplit=2, flags=re.MULTILINE)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ':' in line:
                    k, v = line.split(':', 1); meta[k.strip()] = v.strip()
            body = parts[2]

    html_content = simple_markdown_parser(body)
    
    # Apply smart quotes AFTER all other processing
    html_content = smartquotes(html_content)

    ahash = hashlib.md5(raw_text.encode()).hexdigest()[:8]
    for tag in ['id="fn-', 'href="#fn-', 'id="fnref-', 'href="#fnref-']:
        html_content = html_content.replace(tag, tag.replace('-', f'-{ahash}-'))

    template = temp_path.read_text(encoding="utf-8")
    pub = f'<div class="article-meta">Published {meta.get("date","")}. By {meta.get("author","")}.</div>'
    res = template.replace('$body$', html_content).replace('$published$', pub)
    for k in ['title', 'author', 'date', 'description', 'topic']:
        res = res.replace(f"${k}$", meta.get(k, ''))
    out_path.write_text(res, encoding="utf-8")

if __name__ == "__main__":
    main()
