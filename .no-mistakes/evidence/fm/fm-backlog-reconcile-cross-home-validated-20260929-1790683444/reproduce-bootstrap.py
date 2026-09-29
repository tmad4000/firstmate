import hashlib, os, pathlib, shutil, subprocess, tempfile
root = pathlib.Path.cwd()
evidence = pathlib.Path('/Users/jacob/.no-mistakes/evidence/01M3PHBQ9WSC63QDE15S9TT34K')
base = subprocess.check_output(['git', 'show', 'c5f48e4cad279e6acaf14208522c44e28fac6835:bin/fm-bootstrap.sh'])
transcript = []
with tempfile.TemporaryDirectory(prefix='.bootstrap-verification-', dir=root) as tmp:
    tmp = pathlib.Path(tmp)
    main, mate, separate = [tmp / name for name in ('main', 'mate', 'separate-home')]
    for home in (main, mate, separate):
        for name in ('data', 'state', 'config'):
            (home / name).mkdir(parents=True)
        for name in ('backlog.md', 'done-archive.md'):
            (home / 'data' / name).write_text(f'## Queued\n\n- [ ] {home.name}-1: {home.name} owned record\n')
        shutil.copy(root / '.tasks.toml', home)
    for home in (main, mate):
        shutil.copytree(root / 'bin', home / 'bin', symlinks=True)
        shutil.copy(root / 'AGENTS.md', home)
    books = [p for h in (main, mate, separate) for p in (h / 'data').glob('*.md')]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in books}
    env = {k:v for k,v in os.environ.items() if not k.startswith(('FM_', 'TASKS_AXI_'))}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', FM_BOOTSTRAP_DETECT_ONLY='1', FM_BOOTSTRAP_NETWORK='skip')
    def run(label, invoking, home):
        result = subprocess.run(['bash', str(invoking / 'bin/fm-bootstrap.sh')], cwd=invoking,
                                env=dict(env, FM_HOME=str(home)), capture_output=True, text=True, timeout=30)
        (evidence / (label + '.log')).write_text(result.stdout + result.stderr)
        lines = [l for l in result.stdout.splitlines() if l.startswith('BACKLOG_RECONCILE:')]
        transcript.extend([f'CASE: {label}', f'cwd={invoking}', f'FM_HOME={home} FM_BOOTSTRAP_DETECT_ONLY=1 FM_BOOTSTRAP_NETWORK=skip bash {invoking}/bin/fm-bootstrap.sh',
                           f'exit={result.returncode}', *(lines or ['(no BACKLOG_RECONCILE diagnostics)']), ''])
        assert result.returncode == 0, result.stderr
        return lines
    fixed = (main / 'bin/fm-bootstrap.sh').read_bytes()
    (main / 'bin/fm-bootstrap.sh').write_bytes(base)
    old = run('base-cross-home', main, mate)
    assert len(old) == 2 and all('move it aside' in l for l in old)
    (main / 'bin/fm-bootstrap.sh').write_bytes(fixed)
    assert run('target-cross-home', main, mate) == []
    assert run('target-own-home', mate, mate) == []
    lines = run('target-separate-home', main, separate)
    assert len(lines) == 2
    assert all('never move, rewrite, or delete' in l and 'move it aside' not in l for l in lines)
    for p, digest in before.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest
        transcript.append(f'UNCHANGED sha256={digest} {p.relative_to(tmp)}\n{p.read_text()}')
    transcript.append('All six backlog/archive files remain byte-identical. Temporary fixture homes removed after verification.')
(evidence / 'bootstrap-transcript.txt').write_text('\n'.join(transcript) + '\n')
print('\n'.join(transcript))
