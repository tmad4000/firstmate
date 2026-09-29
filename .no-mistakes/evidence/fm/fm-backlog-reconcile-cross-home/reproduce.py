import os, pathlib, subprocess, tempfile, shutil, hashlib
root = pathlib.Path.cwd()
evidence = pathlib.Path('/Users/jacob/.no-mistakes/evidence/01M3PGGXXHE6SBED643D4GMD5H')
base = subprocess.check_output(['git','show','c5f48e4cad279e6acaf14208522c44e28fac6835:bin/fm-bootstrap.sh'])
transcript = []
with tempfile.TemporaryDirectory(prefix='.bootstrap-check-', dir=root) as tmp:
    fixture = pathlib.Path(tmp)
    for name in ('main', 'mate'):
        home = fixture/name
        shutil.copytree(root/'bin', home/'bin', symlinks=True)
        shutil.copy(root/'AGENTS.md', home/'AGENTS.md')
        shutil.copy(root/'.tasks.toml', home/'.tasks.toml')
        for directory in ('data','state','config'):
            (home/directory).mkdir()
        (home/'data/backlog.md').write_text(f'## In flight\n\n## Queued\n\n- [ ] {name}-1: {name} home own task\n\n## Done\n')
        (home/'data/done-archive.md').write_text(f'## Done\n\n- [x] {name}-done: {name} completed task\n')
    records = list(fixture.glob('*/data/*.md'))
    before = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest() for p in records}
    env = {k:v for k,v in os.environ.items() if not k.startswith(('FM_', 'TASKS_AXI_'))}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', FM_HOME=str(fixture/'mate'), FM_BOOTSTRAP_DETECT_ONLY='1', FM_BOOTSTRAP_NETWORK='skip', FM_TEST_SEAM='1', FM_GATE_REFUSE_BYPASS='1')
    def run(label, home, count):
        command = str(fixture/home/'bin/fm-bootstrap.sh')
        result = subprocess.run([command], cwd=fixture/home, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (evidence/(label+'.log')).write_text(result.stdout)
        lines = [s for s in result.stdout.splitlines() if s.startswith('BACKLOG_RECONCILE:')]
        transcript.append(f'{label}: FM_HOME=<fixture>/mate FM_BOOTSTRAP_DETECT_ONLY=1 FM_BOOTSTRAP_NETWORK=skip <fixture>/{home}/bin/fm-bootstrap.sh\nexit={result.returncode}\n' + ('\n'.join(lines).replace(str(fixture),'<fixture>') if lines else '(no BACKLOG_RECONCILE diagnostics)'))
        assert result.returncode == 0, result.stdout
        assert len(lines) == count, lines
        return lines
    target = (fixture/'main/bin/fm-bootstrap.sh').read_bytes()
    (fixture/'main/bin/fm-bootstrap.sh').write_bytes(base)
    old = run('baseline-cross-home', 'main', 2)
    assert all('move it aside' in s for s in old)
    (fixture/'main/bin/fm-bootstrap.sh').write_bytes(target)
    run('fixed-cross-home', 'main', 0)
    run('fixed-own-home', 'mate', 0)
    # A config-only operational home must still detect possible misplaced rows.
    (fixture/'mate/AGENTS.md').unlink()
    lines = run('fixed-borrowed-code-root', 'main', 2)
    assert all('never move, rewrite, or delete' in s and 'move it aside' not in s for s in lines)
    after = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest() for p in records}
    assert before == after
    transcript.append('All four persisted backlog/archive files remained byte-identical across every invocation.\n' + '\n'.join(f'{p}: SHA256 {sha}' for p,sha in after.items()))
    transcript.append('Scope: real bootstrap executable, isolated checkout-shaped homes, detect-only local phase; network and mutable fleet sweeps excluded.')
(evidence/'bootstrap-transcript.txt').write_text('\n\n'.join(transcript)+'\n')
print('\n\n'.join(transcript))
