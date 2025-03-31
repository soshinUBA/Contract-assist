from main_current_annonymizer import contract_assist
import asyncio

contract_list = [
    "Contracts/contracts_anonymizer_test/M00205393/M00205393"
                 ]

# Async wrapper to process each contract
for contract in contract_list:
    res = contract_assist(contract)
    print("completed ",contract)

