UPDATE currency_rate_update_service 
SET company_id = (SELECT id FROM res_company WHERE name = 'Europ Continents Holding' LIMIT 1);
		

