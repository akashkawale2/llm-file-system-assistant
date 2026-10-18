"""Offline checks: real document parsing and mocked LLM protocol (no API bill)."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import fs_tools
from llm_file_assistant import FileAssistant, dispatch

class ToolTests(unittest.TestCase):
    def test_all_formats(self):
        files = fs_tools.list_files('resumes')
        self.assertEqual(len(files), 8)
        self.assertEqual({f['extension'] for f in files}, {'.pdf', '.docx', '.txt'})
        for item in files:
            result = fs_tools.read_file(item['filepath'])
            self.assertTrue(result['success'], result)
            self.assertIn('FICTIONAL SAMPLE RESUME', result['content'])
        self.assertEqual(len(fs_tools.list_files('resumes', 'PDF')), 3)

    def test_search(self):
        result = fs_tools.search_in_file('resumes/resume_john_doe.pdf', 'pYtHoN')
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['count'], 2)
        self.assertIn('context', result['matches'][0])
        self.assertEqual(fs_tools.search_in_file('resumes/resume_john_doe.pdf', 'C++')['count'], 0)
        self.assertFalse(fs_tools.search_in_file('resumes/resume_john_doe.pdf', '')['success'])

    def test_write_and_errors(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(fs_tools, 'ROOT', Path(directory).resolve()):
            self.assertTrue(fs_tools.write_file('outputs/nested/summary.txt', 'Hello Python')['success'])
            self.assertEqual(fs_tools.read_file('outputs/nested/summary.txt')['content'], 'Hello Python')
            self.assertFalse(fs_tools.read_file('missing.pdf')['success'])
            self.assertFalse(fs_tools.read_file('../outside.txt')['success'])
            self.assertFalse(fs_tools.read_file('.env')['success'])
            self.assertFalse(fs_tools.write_file('resume.pdf', 'text')['success'])
            self.assertEqual(fs_tools.list_files('outputs/nested', '.pdf'), [])
            self.assertFalse(fs_tools.list_files('missing')[0]['success'])
            self.assertFalse(dispatch('write_file', json.dumps({'filepath':'resume.txt','content':'x'}))['success'])
            self.assertFalse(dispatch('read_file', '{broken')['success'])
            self.assertFalse(dispatch('unknown', '{}')['success'])
            Path(directory, 'bad.pdf').write_bytes(b'not a PDF')
            self.assertFalse(fs_tools.read_file('bad.pdf')['success'])

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory).resolve()
            Path(outside, 'private.txt').write_text('secret')
            (root / 'link.txt').symlink_to(Path(outside, 'private.txt'))
            with patch.object(fs_tools, 'ROOT', root):
                self.assertFalse(fs_tools.read_file('link.txt')['success'])

class LoopTests(unittest.TestCase):
    def test_tool_result_returned_to_model(self):
        call = SimpleNamespace(id='call_1', function=SimpleNamespace(
            name='read_file', arguments=json.dumps({'filepath':'resumes/resume_arjun_mehta.txt'})))
        first = SimpleNamespace(tool_calls=[call], content=None, model_dump=lambda **kw: {
            'role':'assistant', 'tool_calls':[{'id':'call_1','type':'function','function':{
                'name':call.function.name,'arguments':call.function.arguments}}]})
        second = SimpleNamespace(tool_calls=None, content='Arjun is a frontend developer.')
        requests = []
        def create(**kwargs):
            requests.append(kwargs)
            message = first if len(requests)==1 else second
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        assistant = FileAssistant(client, 'fake-model')
        self.assertIn('frontend', assistant.ask('Read Arjun resume'))
        tool_message = next(m for m in requests[1]['messages'] if m['role']=='tool')
        self.assertEqual(tool_message['tool_call_id'], 'call_1')
        self.assertTrue(json.loads(tool_message['content'])['success'])

if __name__ == '__main__': unittest.main()
