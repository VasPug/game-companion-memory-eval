import unittest
import run_memory as mem


class MemoryBounds(unittest.TestCase):
    def test_notes_cannot_grow_past_budget_or_reference_unseen_turns(self):
        old = {"1": {"text": "Gate closed", "turn": 10}}
        for change in ({"slot": 2, "text": "x" * 4100, "turn": 15},
                       {"slot": 2, "text": "future claim", "turn": 21}):
            self.assertEqual(mem.apply_notes(old, {"drop": [1], "save": [change]}, 20), (old, False))
        edit = {"slot": 1, "text": "Gate open", "turn": 18}
        self.assertEqual(mem.apply_notes(old, {"drop": [], "save": [edit]}, 20),
                         ({"1": {"text": "Gate open", "turn": 18}}, True))

    def test_checkpoint_has_three_batches_and_only_selected_notes(self):
        recent = mem.recent_window(["old", "one", "two", "three", "future"], 3)
        notes = {"1": {"text": "visible"}, "2": {"text": "unselected"}}
        prompt = mem.answer_prompt(recent, notes, [1], "probe")
        self.assertEqual(recent, "one\ntwo\nthree")
        self.assertIn("visible", prompt)
        self.assertNotIn("unselected", prompt)

if __name__ == "__main__":
    unittest.main()
