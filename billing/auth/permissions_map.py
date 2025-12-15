PAGE_MAPPING = {

    '/_b_a_c_k_e_n_d/ERBilling/erbilling/': 'ER-P-ERB',
    '/_b_a_c_k_e_n_d/ERBilling/doctorlist/': 'ER-P-ERDL',
    '/_b_a_c_k_e_n_d/ERBilling/procedurelist/': 'ER-P-ERPL',
    '/_b_a_c_k_e_n_d/ERBilling/get_next_bill_number/': 'ER-P-ERGNBN',
    '/_b_a_c_k_e_n_d/ERBilling/erreport/': 'ER-P-ERREP',
    r'^/_b_a_c_k_e_n_d/ERBilling/update-status(?:/[^/]+)+/$': 'ER-P-ERUS',
    r'^/_b_a_c_k_e_n_d/ERBilling/printbill/?(\?.*)?$': 'ER-P-ERPB',
    r'^/_b_a_c_k_e_n_d/ERBilling/AccountSummary/?(\?.*)?$': 'ER-P-ERAS',
    r'^/_b_a_c_k_e_n_d/ERBilling/Pharmacy/?(\?.*)?$': 'ER-P-ERP',
 
 


    '/erbilling/': 'ER-P-ERB',
    '/doctorlist/': 'ER-P-ERDL',
    '/procedurelist/': 'ER-P-ERPL',
    '/update-status/': 'ER-P-ERUS',
    '/Pharmacy/': 'ER-P-ERP',
    '/AccountSummary/': 'ER-P-ERAS',
    '/printbill/': 'ER-P-ERPB',
    '/erreport/':'ER-P-ERREP',
    
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



