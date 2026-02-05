#!/usr/bin/env perl
use strict;
use warnings;
use utf8;

# Global storage for inline placeholders to handle recursion correctly
my @inline_data;

# --- UTILS ---

sub simple_hash {
    my ($text) = @_;
    my $hash = 0;
    for my $char (split //, $text) {
        $hash = (($hash << 5) - $hash + ord($char)) & 0xFFFFFFFF;
    }
    return sprintf("%08x", $hash);
}

sub html_escape {
    my ($text) = @_;
    $text =~ s/&/&amp;/g;
    $text =~ s/</&lt;/g;
    $text =~ s/>/&gt;/g;
    $text =~ s/"/&quot;/g;
    return $text;
}

# --- SYNTAX HIGHLIGHTING ---

sub highlight_c {
    my ($code) = @_;
    my @rules = (
        ['cp', qr/#\w+/],
        ['c1', qr{//.*}],
        ['cm', qr{/\*[\s\S]*?\*/}],
        ['s',  qr/"(?:\\.|[^"\\])*"/],
        ['m',  qr/\b0x[0-9a-fA-F]+\b|\b\d+\b/],
        ['k',  qr/\b(?:int|char|void|if|else|while|for|return|struct|static|extern|switch|case|break|continue|typedef|const|unsigned|long|short|default)\b/],
        ['nf', qr/\b\w+(?=\s*\()/],
        ['o',  qr/[=+\-*\/%&|^!<>?]/],
    );
    my $master_pattern = join '|', map { "(?<$_->[0]>$_->[1])" } @rules;
    my @parts; my $last_pos = 0;
    while ($code =~ /$master_pattern/g) {
        my $start = $-[0]; my $end = $+[0];
        if ($start > $last_pos) { push @parts, html_escape(substr($code, $last_pos, $start - $last_pos)); }
        my $matched_text = substr($code, $start, $end - $start);
        my $class_name;
        for my $rule (@rules) { if (defined $+{$rule->[0]}) { $class_name = $rule->[0]; last; } }
        push @parts, qq{<span class="$class_name">} . html_escape($matched_text) . '</span>';
        $last_pos = $end;
    }
    push @parts, html_escape(substr($code, $last_pos)) if $last_pos < length($code);
    return join '', @parts;
}

sub highlight_python {
    my ($code) = @_;
    my @rules = (
        ['c1', qr/#.*/],
        ['s',  qr/"{3}[\s\S]*?"{3}|'{3}[\s\S]*?'{3}|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/],
        ['cp', qr/@\w+/],
        ['k',  qr/\b(?:def|class|if|elif|else|while|for|return|import|from|as|try|except|finally|with|lambda|yield|pass|break|continue|in|is|not|and|or|True|False|None|global|nonlocal|assert|del|raise)\b/],
        ['nf', qr/\b\w+(?=\s*\()/],
        ['m',  qr/\b\d+\b|\b0x[0-9a-fA-F]+\b/],
        ['o',  qr/[=+\-*\/%&|^!<>~]/],
    );
    my $master_pattern = join '|', map { "(?<$_->[0]>$_->[1])" } @rules;
    my @parts; my $last_pos = 0;
    while ($code =~ /$master_pattern/g) {
        my $start = $-[0]; my $end = $+[0];
        if ($start > $last_pos) { push @parts, html_escape(substr($code, $last_pos, $start - $last_pos)); }
        my $matched_text = substr($code, $start, $end - $start);
        my $class_name;
        for my $rule (@rules) { if (defined $+{$rule->[0]}) { $class_name = $rule->[0]; last; } }
        push @parts, qq{<span class="$class_name">} . html_escape($matched_text) . '</span>';
        $last_pos = $end;
    }
    push @parts, html_escape(substr($code, $last_pos)) if $last_pos < length($code);
    return join '', @parts;
}

# --- BLOCK PARSERS ---

sub render_indented_code_blocks {
    my ($text) = @_;
    my @lines = split /\n/, $text;
    my (@result, @buffer);
    for my $line (@lines) {
        if (($line =~ /^    / || $line =~ /^\t/) && ($line =~ /\S/ || @buffer)) {
            my $stripped = $line =~ /^    / ? substr($line, 4) : substr($line, 1);
            push @buffer, html_escape($stripped);
        } else {
            if (@buffer) {
                while (@buffer && $buffer[-1] !~ /\S/) { pop @buffer; }
                push @result, "<pre><code>" . join("\n", @buffer) . "</code></pre>\n\n";
                @buffer = ();
            }
            push @result, $line;
        }
    }
    push @result, "<pre><code>" . join("\n", @buffer) . "</code></pre>\n\n" if @buffer;
    return join "\n", @result;
}

sub render_blockquotes {
    my ($text) = @_;
    my @lines = split /\n/, $text;
    my (@result, @buffer);
    for my $line (@lines) {
        if ($line =~ /^\s*>/) {
            my $content = $line; $content =~ s/^\s*>\s?//;
            push @buffer, $content;
        } else {
            if (@buffer) {
                push @result, "<blockquote>\n" . wrap_loose_paragraphs(render_blocks(join("\n", @buffer))) . "\n</blockquote>\n\n";
                @buffer = ();
            }
            push @result, $line;
        }
    }
    push @result, "<blockquote>\n" . wrap_loose_paragraphs(render_blocks(join("\n", @buffer))) . "\n</blockquote>\n\n" if @buffer;
    return join "\n", @result;
}

sub render_tables {
    my ($text) = @_;
    my @lines = split /\n/, $text;
    my @output; my $i = 0;
    while ($i < @lines) {
        my $line = $lines[$i]; $line =~ s/^\s+|\s+$//g;
        if (($line =~ /^\|/ || $line =~ /\|/) && $i + 1 < @lines) {
            my $sep_line = $lines[$i + 1]; $sep_line =~ s/^\s+|\s+$//g;
            if ($sep_line =~ /^\|?[\s|:-]+\|?$/ && $sep_line =~ /\|/) {
                $sep_line =~ s/^\||\|$//g;
                my @sep_parts = map { s/^\s+|\s+$//gr } split /\|/, $sep_line;
                my @aligns = map { /^:.*:$/ ? 'center' : /:$/ ? 'right' : 'left' } @sep_parts;
                $line =~ s/^\||\|$//g;
                my @headers = map { s/^\s+|\s+$//gr } split /\|/, $line;
                my $n = scalar @headers;
                my $tbl = "<table><thead><tr>" . join('', map { qq{<th style="text-align:$aligns[$_]">} . render_inline($headers[$_]) . '</th>' } 0..$#headers) . "</tr></thead><tbody>\n";
                $i += 2;
                while ($i < @lines && $lines[$i] =~ /\|/) {
                    my $row = $lines[$i]; $row =~ s/^\s+|\s+$//g; $row =~ s/^\||\|$//g;
                    my @cells = map { s/^\s+|\s+$//gr } split /\|/, $row;
                    $tbl .= "<tr>" . join('', map { qq{<td style="text-align:$aligns[$_]">} . render_inline($cells[$_] // '') . '</td>' } 0..$n-1) . "</tr>\n";
                    $i++;
                }
                push @output, $tbl . "</tbody></table>\n\n"; next;
            }
        }
        push @output, $lines[$i]; $i++;
    }
    return join "\n", @output;
}

sub render_lists {
    my ($text) = @_;
    my @lines = split /\n/, $text;
    my @output; my $i = 0;
    while ($i < @lines) {
        if ($lines[$i] =~ /^(\s*)(\d+\.|[*+-])(\s+)(.*)/) {
            my ($indent_str, $marker, $spacing, $first) = ($1, $2, $3, $4);
            my $indent_len = length($indent_str);
            my $tag = $marker =~ /^\d/ ? 'ol' : 'ul';
            my (@items, @current_item);
            push @current_item, $first; $i++;
            while ($i < @lines) {
                if ($lines[$i] =~ /^\Q$indent_str\E(\d+\.|[*+-])(\s+)(.*)/) {
                    push @items, join("\n", @current_item);
                    $marker = $1; $spacing = $2; @current_item = ($3); $i++;
                } elsif ($lines[$i] =~ /^\s*$/) {
                    # Only consume blank line if next non-blank line is indented
                    my $next = $i + 1;
                    while ($next < @lines && $lines[$next] =~ /^\s*$/) { $next++; }
                    if ($next < @lines && $lines[$next] =~ /^(\s+)/ && length($1) > $indent_len) {
                        push @current_item, map { "" } ($i .. $next - 1); $i = $next;
                    } else { last; }
                } elsif ($lines[$i] =~ /^(\s+)/ && length($1) > $indent_len) {
                    my $l = $lines[$i];
                    my $strip = $indent_len + length($marker) + length($spacing);
                    $l =~ s/^\s{0,$strip}//; push @current_item, $l; $i++;
                } else { last; }
            }
            push @items, join("\n", @current_item);
            my @li = map { "<li>\n" . wrap_loose_paragraphs(render_blocks($_)) . "\n</li>" } @items;
            push @output, "<$tag>\n" . join("\n", @li) . "\n</$tag>\n\n";
        } else { push @output, $lines[$i]; $i++; }
    }
    return join "\n", @output;
}

# --- INLINE & WRAPPING ---

sub render_inline {
    my ($text) = @_;
    $text =~ s/`([^`]+)`/push(@inline_data, '<code>' . html_escape($1) . '<\/code>'); "\x01P" . $#inline_data . "\x01"/eg;
    $text =~ s/!\[([^\]]*)\]\(([^)]+)\)/push(@inline_data, qq{<img src="$2" alt="$1">}); "\x01P" . $#inline_data . "\x01"/eg;
    $text =~ s/\[([^\]]+)\]\(([^)]+)\)/
        my $inner = render_inline($1);
        push(@inline_data, qq{<a href="$2">$inner<\/a>}); "\x01P" . $#inline_data . "\x01"
    /eg;
    $text =~ s/---/&mdash;/g; $text =~ s/--/&ndash;/g;
    $text =~ s/\*\*\*([\s\S]*?)\*\*\*/<strong><em>$1<\/em><\/strong>/g;
    $text =~ s/___([\s\S]*?)___/<strong><em>$1<\/em><\/strong>/g;
    $text =~ s/\*\*([\s\S]*?)\*\*/<strong>$1<\/strong>/g;
    $text =~ s/__([\s\S]*?)__/<strong>$1<\/strong>/g;
    $text =~ s/\*([\s\S]*?)\*/<em>$1<\/em>/g;
    $text =~ s/_([\s\S]*?)_/<em>$1<\/em>/g;
    # Multi-pass restoration for nested elements
    while ($text =~ /\x01P(\d+)\x01/) { $text =~ s/\x01P(\d+)\x01/$inline_data[$1]/eg; }
    return $text;
}

sub smartquotes {
    my ($text) = @_;
    my @prot;
    $text =~ s/(<[^>]+>|<code>.*?<\/code>|<pre>.*?<\/pre>)/push(@prot, $1); "\x02P" . $#prot . "\x02"/egs;
    $text =~ s/(^|[\s\(\[\{])"/$1&ldquo;/g; $text =~ s/"/&rdquo;/g;
    $text =~ s/(^|[\s\(\[\{])'/$1&lsquo;/g; $text =~ s/'/&rsquo;/g;
    while ($text =~ /\x02P(\d+)\x02/) { $text =~ s/\x02P(\d+)\x02/$prot[$1]/egs; }
    return $text;
}

sub wrap_loose_paragraphs {
    my ($text) = @_;
    $text =~ s/^\s+|\s+$//g;
    return "" unless $text;
    my @blocks = split /\n\n+/, $text;
    my @proc;
    for my $b (@blocks) {
        my $t = $b; $t =~ s/^\s+|\s+$//g; next unless $t;
        # If it looks like HTML block or a fenced code placeholder, don't wrap in <p>
        if ($t =~ /^<(div|table|h\d|pre|ol|ul|li|blockquote|hr|section)|\x00FENCEDCODE/) { push @proc, $t; }
        else { push @proc, '<p>' . render_inline($t) . '</p>'; }
    }
    return join "\n", @proc;
}

sub render_blocks {
    my ($text) = @_;
    $text = render_lists($text);
    $text = render_indented_code_blocks($text);
    $text = render_blockquotes($text);
    $text = render_tables($text);
    $text =~ s{^(#{1,6})\s+(.*)$}{
        my $lvl = length($1); my $txt = $2; $txt =~ s/^\s+|\s+$//g;
        my $hid = lc($txt); $hid =~ s/\s+/-/g; $hid =~ s/[^\w\-]//g;
        "<h$lvl id=\"$hid\">$txt</h$lvl>\n\n";
    }mge;
    return $text;
}

# --- CORE ---

sub simple_markdown_parser {
    my ($md) = @_;
    @inline_data = ();
    my %fn; my @filtered; my @lines = split /\n/, $md;
    for (my $i=0; $i < @lines; $i++) {
        if ($lines[$i] =~ /^\[\^([^\]]+)\]:\s*(.*)/) {
            my $id = $1; my @c = ($2); $i++;
            while ($i < @lines && ($lines[$i] =~ /^\s/ || $lines[$i] eq "")) {
                my $l = $lines[$i]; $l =~ s/^\s+//; push @c, $l; $i++;
            }
            $fn{$id} = join(" ", @c); $i--;
        } else { push @filtered, $lines[$i]; }
    }
    $md = join "\n", @filtered;
    my @fenced;
    $md =~ s{^([ \t]*)```(\w*)[ \t]*\n(.*?)\n\1```[ \t]*$}{
        my ($ind, $lang, $code) = ($1, lc($2||'text'), $3);
        my $h = ($lang eq 'c') ? highlight_c($code) : ($lang =~ /python|py/) ? highlight_python($code) : html_escape($code);
        push @fenced, qq{<div class="codehilite"><pre><code class="language-$lang">$h</code></pre></div>\n\n};
        $ind . "\x00FENCEDCODE" . $#fenced . "\x00"; 
    }msge;

    $md = wrap_loose_paragraphs(render_blocks($md));

    my @fn_ord; my %fn_seen;
    $md =~ s/\[\^([^\]]+)\]/
        my $id = $1;
        if (!$fn_seen{$id}) { push @fn_ord, $id; $fn_seen{$id} = scalar @fn_ord; }
        my $num = $fn_seen{$id};
        qq{<sup class="footnote-ref"><a href="#fn-$id" id="fnref-$id">[$num]<\/a><\/sup>};
    /ge;

    # Restore Fenced Code blocks after paragraph wrapping
    $md =~ s/\x00FENCEDCODE(\d+)\x00/$fenced[$1]/g;

    if (@fn_ord) {
        my @items;
        for my $id (@fn_ord) {
            my $num = $fn_seen{$id};
            my $content = render_inline($fn{$id} // "[Missing definition]");
            push @items, qq{<li id="fn-$id" value="$num">$content <a href="#fnref-$id">↩</a></li>};
        }
        $md .= "\n<hr><section class=\"footnotes\"><ol>" . join('', @items) . "</ol></section>";
    }
    return $md;
}

sub main {
    my ($md_path, $temp_path, $out_path) = @ARGV;
    open my $mfh, '<:encoding(UTF-8)', $md_path or die $!;
    my $raw = do { local $/; <$mfh> }; close $mfh;
    my %meta; my $body = $raw;
    if ($raw =~ /^---\s*\n(.*?)\n---\s*\n(.*)/s) {
        my ($m, $c) = ($1, $2); $body = $c;
        for (split /\n/, $m) { if (/^([^:]+):\s*(.*)/) { $meta{$1} = $2; } }
    }
    my $html = smartquotes(simple_markdown_parser($body));
    my $ahash = substr(simple_hash($raw), 0, 8);
    for ('id="fn-', 'href="#fn-', 'id="fnref-', 'href="#fnref-') {
        my $r = $_; $r =~ s/-$/-$ahash-/; $html =~ s/\Q$_\E/$r/g;
    }
    open my $tfh, '<:encoding(UTF-8)', $temp_path or die $!;
    my $tpl = do { local $/; <$tfh> }; close $tfh;
    $tpl =~ s/\$body\$/$html/g;
    $tpl =~ s/\$published\$/'<div class="article-meta">Published '.($meta{date}||'').'. By '.($meta{author}||'').'.<\/div>'/eg;
    for (qw(title author date description topic)) { my $v = $meta{$_}||''; $tpl =~ s/\$\Q$_\E\$/$v/g; }
    open my $ofh, '>:encoding(UTF-8)', $out_path or die $!;
    print $ofh $tpl; close $ofh;
}

main();
