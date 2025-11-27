PAGE_MAPPING = {

    '/_b_a_c_k_e_n_d/ER/erbilling/': 'ER-P-ERB',
    '/_b_a_c_k_e_n_d/ER/doctorlist/': 'ER-P-ERDL',
    '/_b_a_c_k_e_n_d/ER/procedurelist/': 'ER-P-ERPL',
    r'^/_b_a_c_k_e_n_d/ER/update-status/?(\?.*)?$': 'ER-P-ERUS',
    '/_b_a_c_k_e_n_d/ER/Pharmacy/': 'ER-P-ERP',
    r'^/_b_a_c_k_e_n_d/ER/printbill/?(\?.*)?$': 'ER-P-ERPB',
    r'^/_b_a_c_k_e_n_d/ER/AccountSummary/?(\?.*)?$': 'ER-P-ERAS',


    '/erbilling/': 'ER-P-ERB',
    '/doctorlist/': 'ER-P-ERDL',
    '/procedurelist/': 'ER-P-ERPL',
    '/update-status/': 'ER-P-ERUS',
    '/Pharmacy/': 'ER-P-ERP',
    '/AccountSummary/': 'ER-P-ERAS',
    '/printbill/': 'ER-P-ERPB',
    
}



PAGE_ACTION_MAPPING = {
    'xxx': {
        'DELETE':'RWD',
    },
}

GEN_ACTION_MAPPING = {
    'POST': 'RW',
    'PUT': 'RW',
    'PATCH': 'RW',
    'DELETE': 'RW',
    'GET': 'R',
}



