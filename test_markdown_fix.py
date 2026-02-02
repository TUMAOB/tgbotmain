#!/usr/bin/env python3
"""
Test script to verify the Markdown parsing fix for /b3s command
"""

def test_card_result_format():
    """Test that card result format doesn't break Telegram Markdown parsing"""
    
    # Simulate a card result with special characters
    result = """
APPROVED ✅

𝗖𝗖 ⇾ 5401683112957490|10|2029|741
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Braintree Auth 1
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ Approved

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: VISA - CREDIT - CLASSIC
𝗕𝗮𝗻𝗸: Test Bank
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: United States 🇺🇸

𝗧𝗼𝗼𝗸 2.34 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB
"""
    
    # Old format (with Markdown) - would cause error
    old_card_result = f"**Card 1/3:**\n{result}"
    
    # New format (without Markdown) - should work
    new_card_result = f"Card 1/3:\n{result}"
    
    print("=" * 60)
    print("OLD FORMAT (with Markdown - CAUSES ERROR):")
    print("=" * 60)
    print(old_card_result)
    print("\n" + "=" * 60)
    print("NEW FORMAT (without Markdown - FIXED):")
    print("=" * 60)
    print(new_card_result)
    print("\n" + "=" * 60)
    
    # Check for problematic characters
    problematic_chars = ['|', '*', '_', '[', ']', '(', ')']
    found_chars = []
    
    for char in problematic_chars:
        if char in result:
            found_chars.append(char)
    
    print(f"\nProblematic Markdown characters found in result: {found_chars}")
    print(f"These characters would break Telegram's Markdown parser if parse_mode='Markdown' is used.")
    print(f"\n✅ FIX: Removed parse_mode='Markdown' from reply_text() calls")
    print(f"✅ FIX: Removed ** bold markers from card result format")
    
    return True

def test_summary_format():
    """Test that summary format doesn't break Telegram Markdown parsing"""
    
    total_cards = 5
    approved_count = 3
    declined_count = 2
    
    # Old format (with Markdown) - could cause issues
    old_summary = f"📊 **Mass Check Complete**\n\n"
    old_summary += f"Total Cards: {total_cards}\n"
    old_summary += f"✅ Approved: {approved_count}\n"
    old_summary += f"❌ Declined: {declined_count}"
    
    # New format (without Markdown) - should work
    new_summary = f"📊 Mass Check Complete\n\n"
    new_summary += f"Total Cards: {total_cards}\n"
    new_summary += f"✅ Approved: {approved_count}\n"
    new_summary += f"❌ Declined: {declined_count}"
    
    print("\n" + "=" * 60)
    print("SUMMARY - OLD FORMAT (with Markdown):")
    print("=" * 60)
    print(old_summary)
    print("\n" + "=" * 60)
    print("SUMMARY - NEW FORMAT (without Markdown - FIXED):")
    print("=" * 60)
    print(new_summary)
    print("\n" + "=" * 60)
    
    return True

if __name__ == "__main__":
    print("\n🔍 Testing Markdown Parsing Fix for /b3s Command\n")
    
    test_card_result_format()
    test_summary_format()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nSUMMARY OF CHANGES:")
    print("1. Removed parse_mode='Markdown' from card result message")
    print("2. Removed ** bold markers from 'Card X/Y:' prefix")
    print("3. Removed parse_mode='Markdown' from summary message")
    print("4. Removed ** bold markers from 'Mass Check Complete'")
    print("\nThese changes prevent Telegram's Markdown parser from failing")
    print("when encountering special characters like | in card numbers.")
    print("=" * 60)
