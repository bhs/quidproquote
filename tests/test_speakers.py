import unittest

from pairing_site import speakers

OFFICIALS = [
    {"name": "Matt Dorsey", "surname": "Dorsey", "district": "6", "office": "Supervisor", "exact": ["DORSEY"], "garbled": []},
    {"name": "Alan Wong", "surname": "Wong", "district": "4", "office": "Supervisor", "exact": ["WONG"], "garbled": ["WANG"]},
    {"name": "Bilal Mahmood", "surname": "Mahmood", "district": "5", "office": "Supervisor", "exact": ["MAHMOOD"], "garbled": ["MAMU"]},
    {"name": "Jackie Fielder", "surname": "Fielder", "district": "9", "office": "Supervisor", "exact": ["FIELDER"], "garbled": []},
    {"name": "Connie Chan", "surname": "Chan", "district": "1", "office": "Supervisor", "exact": ["CHAN"], "garbled": []},
    {"name": "Daniel Lurie", "surname": "Lurie", "district": "", "office": "Mayor", "exact": ["LURIE"], "garbled": []},
]
ROSTER = speakers.Roster(OFFICIALS)


def doc_of(text):
    return speakers.Doc([("00:00:%02d" % i, t.strip()) for i, t in enumerate(text.split("|"))])


class Cues(unittest.TestCase):
    def test_opener_roll_call_and_mention(self):
        d = doc_of(">> SUPERVISOR DORSEY THANK YOU PRESIDENT. I WANT TO THANK SUPERVISOR WONG FOR THIS. "
                   "ON THE ROLL SUPERVISOR CHAN CHAN PRESENT")
        regions = speakers.find_regions(d, ROSTER)
        self.assertEqual([r["official"] for r in regions], ["Matt Dorsey"])
        self.assertNotIn("PRESENT", d.text[regions[0]["start"]:regions[0]["end"]].split("CHAN")[0])

    def test_a_turn_runs_to_the_next_cue_and_is_low_doubt(self):
        d = doc_of(">> SUPERVISOR WONG THANK YOU. COLLEAGUES, THE PARCEL TAX.|IT HELPS.|>> SUPERVISOR DORSEY THANK YOU.")
        regions = speakers.find_regions(d, ROSTER)
        self.assertEqual([r["official"] for r in regions], ["Alan Wong", "Matt Dorsey"])
        self.assertTrue(regions[0]["bounded"])
        pos = d.text.find("PARCEL TAX")
        self.assertEqual(speakers.credit_tier(d, regions[0], pos)[0], "low")

    def test_a_garbled_spelling_is_never_low(self):
        d = doc_of(">> SUPERVISOR WANG THANK YOU. COLLEAGUES, THE PARCEL TAX.|>> SUPERVISOR DORSEY THANK YOU.")
        reg = speakers.find_regions(d, ROSTER)[0]
        self.assertEqual(reg["official"], "Alan Wong")
        self.assertEqual(speakers.credit_tier(d, reg, d.text.find("PARCEL"))[0], "medium")

    def test_a_given_name_before_a_garbled_surname_is_a_cue_with_doubt(self):
        d = doc_of(">> MADAM CHAIR, THANK YOU AND TODAY WE HAVE SUPERVISOR|BALA MAMU HERE. >> WELCOME. >> THIS MEASURE GIVES VOTERS A CHOICE.")
        regions = speakers.find_regions(d, ROSTER)
        self.assertEqual([r["official"] for r in regions], ["Bilal Mahmood"])
        self.assertNotEqual(speakers.credit_tier(d, regions[0], d.text.find("THIS MEASURE"))[0], "low")

    def test_an_unlisted_spelling_is_matched_to_the_roster_by_spelling(self):
        d = doc_of(">> SUPERVISOR FIELDERS THANK YOU. COLLEAGUES, HELLO.|>> SUPERVISOR DORSEY THANK YOU.")
        self.assertEqual(speakers.find_regions(d, ROSTER)[0]["official"], "Jackie Fielder")

    def test_chan_is_capped_at_medium_without_a_district_cue(self):
        d = doc_of(">> SUPERVISOR CHAN THANK YOU. COLLEAGUES, THE PARCEL TAX.|>> SUPERVISOR DORSEY THANK YOU.")
        reg = speakers.find_regions(d, ROSTER)[0]
        self.assertEqual(speakers.credit_tier(d, reg, d.text.find("PARCEL"))[0], "medium")

    def test_a_self_introduction_closes_a_turn(self):
        d = doc_of(">> SUPERVISOR DORSEY THANK YOU. COLLEAGUES, WELCOME.|>> GOOD MORNING. MY NAME IS ANN LEE AND I SPEAK ON FIREWORKS.")
        reg = speakers.find_regions(d, ROSTER)[0]
        self.assertNotIn("FIREWORKS", d.text[reg["start"]:reg["end"]])

    def test_the_mayors_opening_remarks_are_one_low_doubt_turn(self):
        d = doc_of("THE APPEARANCE BY THE HONORABLE MAYOR DANIEL LURIE.|WELCOME, MR. MAYOR. DO YOU HAVE ANY OPENING|"
                   "REMARKS? I DO. GOOD AFTERNOON. MUNI RIDERSHIP IS UP.|>> THANK YOU, MAYOR LURIE. NEXT.")
        reg = [r for r in speakers.find_regions(d, ROSTER) if r["kind"] == "mayor-opening"]
        self.assertEqual(len(reg), 1)
        self.assertEqual(reg[0]["official"], "Daniel Lurie")
        self.assertIn("MUNI RIDERSHIP", d.text[reg[0]["start"]:reg[0]["end"]])
        self.assertEqual(speakers.credit_tier(d, reg[0], d.text.find("MUNI"))[0], "low")


if __name__ == "__main__":
    unittest.main()
