from main_current_annonymizer import contract_assist
import asyncio

contract_list = [
    # "Contracts/OneDrive_1_21-02-2025/Global Order Management & Royalty/Non-English/German/Individuals/M00222652.pdf",
                 "Contracts/M00215821.pdf",
                #  "Contracts/OneDrive_1_21-02-2025/Global Order Management & Royalty/Non-English/German/Individuals/M00221232.pdf",
                # "Contracts/OneDrive_1_21-02-2025/Global Order Management & Royalty/Non-English/German/Individuals/M00223219-COMPLETED Hamburg Commercial Bank AG MT Fonts Enterprise License 2024-12-20-M00223219.pdf",
                #  "Contracts/OneDrive_1_21-02-2025/Global Order Management & Royalty/Non-English/German/Individuals/M00223429-COMPLETED JUNGBUNZLAUER SUISSE AG MT Fonts Enterprise License 2025-01-10.pdf",
                # "Contracts/OneDrive_1_21-02-2025/Global Order Management & Royalty/Non-English/German/Individuals/M00223513-COMPLETED Stadtwerke Göttingen AG MT Fonts Enterprise License 2025-02-01.pdf"
                 ]

# Async wrapper to process each contract
for contract in contract_list:
    res = contract_assist(contract)
    print("completed ",contract)

