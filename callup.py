from main_current_annonymizer import contract_assist
import asyncio

contract_list = ["Contracts/OneDrive_1_21-02-2025/Global Order Management & Royalty/Non-English/German/Individuals/M00216210.pdf"
                 ]

# Async wrapper to process each contract
for contract in contract_list:
    res = contract_assist(contract)
    print("completed ",contract)

