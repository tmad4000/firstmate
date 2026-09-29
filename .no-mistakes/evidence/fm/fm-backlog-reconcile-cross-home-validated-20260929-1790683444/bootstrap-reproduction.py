import os, pathlib, tempfile, shutil, subprocess, hashlib
root = pathlib.Path.cwd()
evidence = pathlib.Path('/Users/jacob/.no-mistakes/evidence/01M3PHZ3TWPPVKNE4SFHQZY46J')
base = subprocess.check_output(['git','show','c5f48e4cad279e6acaf14208522c44e28fac6835:bin/fm-bootstrap.sh'])
target = (root/'bin/fm-bootstrap.sh').read_bytes()
logs = []
with tempfile.TemporaryDirectory(prefix='.bootstrap-test-', dir=root) as temp:
    temp = pathlib.Path(temp)
    main, mate = temp/'main', temp/'mate'
    for home in (main, mate):
        shutil.copytree(root/'bin', home/'bin', symlinks=True)
        shutil.copy(root/'AGENTS.md', home/'AGENTS.md')
        shutil.copy(root/'.tasks.toml', home/'.tasks.toml')
        for d in ('data','state','config'): (home/d).mkdir()
        for name in ('backlog.md','done-archive.md'):
            (home/'data'/name).write_text(f'## Queued\n\n- [ ] {home.name}-1: {home.name} exclusive task\n')
    books = list(main.glob('data/*.md')) + list(mate.glob('data/*.md'))
    def hashes(): return {str(p.relative_to(temp)):hashlib.sha256(p.read_bytes()).hexdigest() for p in books}
    before = hashes()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('FM_', 'TASKS_AXI_'))}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', FM_HOME=str(mate), FM_BOOTSTRAP_DETECT_ONLY='1', FM_BOOTSTRAP_NETWORK='skip')
    def run(label, script, extra=None):
        e = dict(env); e.update(extra or {})
        p = subprocess.run(['bash', str(script)], cwd=script.parent.parent, env=e, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        logs.append(f'=== {label} ===\nFM_HOME={e["FM_HOME"]} FM_BOOTSTRAP_DETECT_ONLY=1 FM_BOOTSTRAP_NETWORK=skip bash {script}\nexit={p.returncode}\n{p.stdout}')
        assert p.returncode == 0, p.stdout
        return [line for line in p.stdout.splitlines() if line.startswith('BACKLOG_RECONCILE: code-root')]
    (main/'bin/fm-bootstrap.sh').write_bytes(base)
    old = run('BASE: main bootstrap targeting secondmate', main/'bin/fm-bootstrap.sh')
    assert len(old)==2 and all('move it aside' in s for s in old)
    (main/'bin/fm-bootstrap.sh').write_bytes(target)
    fixed = run('TARGET: main bootstrap targeting secondmate', main/'bin/fm-bootstrap.sh')
    assert fixed == []
    own = run('TARGET: secondmate bootstrap targeting itself', mate/'bin/fm-bootstrap.sh')
    assert own == []
    relocated = mate/'relocated'; relocated.mkdir()
    for name in ('backlog.md','done-archive.md'):
        p=relocated/name; p.write_text('## Queued\n\n- [ ] relocated-1: separate task\n'); books.append(p)
    # Capture relocated books alongside the original four before checking override behavior.
    assert all(hashes()[k]==v for k,v in before.items())
    before=hashes()
    warnings=run('TARGET: relocated data retains cautious diagnostics', main/'bin/fm-bootstrap.sh', {'FM_DATA_OVERRIDE':str(relocated)})
    assert len(warnings)==2
    assert all('never move, rewrite, or delete it on this line alone' in s and 'move it aside' not in s for s in warnings)
    assert before==hashes()
    logs.append('Record integrity: all six backlog/archive SHA-256 digests unchanged.\n'+'\n'.join(f'{k} {v}' for k,v in hashes().items()))
    logs.append('Observed regression: base emits two destructive cross-home warnings; target emits none from either checkout. Relocated-data warnings remain cautious and every book is preserved.')
(evidence/'bootstrap-cli-transcript.txt').write_text('\n\n'.join(logs)+'\n')
print(logs[-1])
