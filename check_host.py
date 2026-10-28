import sys; sys.path.insert(0, '.')
from app import create_app
app, socketio = create_app()

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_type'] = 'host'
        sess['host_id'] = 1
        sess['host_username'] = 'admin'
    resp = client.get('/host/dashboard')
    html = resp.data.decode('utf-8')
    print('Status:', resp.status_code)
    print('Contains Question Bank:', 'Question Bank' in html)
    print('Contains #1:', '#1' in html)
    print('Contains CRYARITHMETIC:', 'CRYARITHMETIC' in html)
    print('Table rows count:', html.count('id="q-row-'))
