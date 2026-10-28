import unittest
import requests
import time

class TestLiveE2E(unittest.TestCase):
    """
    Live End-to-End verification against a running server.
    Skips automatically if the server is not running on 127.0.0.1:5000.
    """
    @classmethod
    def setUpClass(cls):
        cls.base_url = 'http://127.0.0.1:5000'
        try:
            requests.get(f'{cls.base_url}/', timeout=1.0)
        except Exception:
            raise unittest.SkipTest("Live server not running at http://127.0.0.1:5000 - skipping live E2E test.")

    def test_live_auction_and_bidding(self):
        base_url = self.base_url

        # 1. Host session
        s_host = requests.Session()
        r = s_host.get(f'{base_url}/')
        self.assertTrue('/team/login' in r.url or r.status_code == 200)

        r_login = s_host.post(f'{base_url}/host/login', data={'username': 'admin', 'password': 'host123'}, allow_redirects=True)
        self.assertTrue('host/dashboard' in r_login.url or 'Host Control Room' in r_login.text)

        # 2. If an auction is already LIVE, cancel it first
        r_state = s_host.get(f'{base_url}/api/host/state')
        state_data = r_state.json()
        if state_data.get('active_auction'):
            s_host.post(f'{base_url}/api/host/cancel-auction', json={'auction_id': state_data['active_auction']['id']})
            r_state = s_host.get(f'{base_url}/api/host/state')
            state_data = r_state.json()
        questions = state_data.get('questions', [])
        available_q = next((q for q in questions if q['status'] == 'AVAILABLE'), None)
        self.assertIsNotNone(available_q, "No available questions found to auction.")
        target_qid = available_q['id']

        r_start = s_host.post(f'{base_url}/api/host/start-auction', json={'question_id': target_qid})
        data_start = r_start.json()
        self.assertTrue(data_start.get('success'), f"Failed to start auction: {data_start}")
        auction_id = data_start['auction_id']

        # 3. Team 1 logs in and bids
        s_t1 = requests.Session()
        r_t1_login = s_t1.post(f'{base_url}/team/login', data={'team_code': 'TEAM001', 'password': 'TEST@123'})
        self.assertIn(r_t1_login.status_code, (200, 302))

        r_bid1 = s_t1.post(f'{base_url}/api/team/bid', json={'auction_id': auction_id})
        data_bid1 = r_bid1.json()
        self.assertTrue(data_bid1.get('success'), f"Team 1 bid failed: {data_bid1}")

        # 4. Team 2 logs in and bids
        s_t2 = requests.Session()
        r_t2_login = s_t2.post(f'{base_url}/team/login', data={'team_code': 'TEAM002', 'password': 'TEST@123'})
        self.assertIn(r_t2_login.status_code, (200, 302))

        r_bid2 = s_t2.post(f'{base_url}/api/team/bid', json={'auction_id': auction_id})
        data_bid2 = r_bid2.json()
        self.assertTrue(data_bid2.get('success'), f"Team 2 bid failed: {data_bid2}")

        # 5. Cancel or wait
        r_cancel = s_host.post(f'{base_url}/api/host/cancel-auction', json={'auction_id': auction_id})
        self.assertTrue(r_cancel.json().get('success'))

if __name__ == '__main__':
    unittest.main()
