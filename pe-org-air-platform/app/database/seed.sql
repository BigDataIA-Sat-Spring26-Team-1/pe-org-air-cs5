-- Seed Data
DELETE FROM industries;
INSERT INTO industries (id, name, sector, h_r_base) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'Manufacturing', 'Industrials', 68),
('550e8400-e29b-41d4-a716-446655440002', 'Healthcare Services', 'Healthcare', 78),
('550e8400-e29b-41d4-a716-446655440003', 'Business Services', 'Services', 75),
('550e8400-e29b-41d4-a716-446655440004', 'Retail', 'Consumer', 56),
('550e8400-e29b-41d4-a716-446655440005', 'Financial Services', 'Financial', 72),
('550e8400-e29b-41d4-a716-446655440006', 'Technology', 'Technology', 92);

-- Seed Companies
DELETE FROM companies;
INSERT INTO companies (id, name, ticker, industry_id, market_cap_percentile, position_factor) VALUES
('c017026e-ab4b-451c-a1a9-e80fd4de0794', 'NVIDIA Corporation', 'NVDA', '550e8400-e29b-41d4-a716-446655440006', 0.99, 1.0),
('c017026e-ab4b-451c-a1a9-e80fd4de0795', 'JPMorgan Chase & Co.', 'JPM', '550e8400-e29b-41d4-a716-446655440005', 0.95, 0.6),
('c017026e-ab4b-451c-a1a9-e80fd4de0796', 'Walmart Inc.', 'WMT', '550e8400-e29b-41d4-a716-446655440004', 0.92, 0.6),
('c017026e-ab4b-451c-a1a9-e80fd4de0797', 'General Electric Company', 'GE', '550e8400-e29b-41d4-a716-446655440001', 0.60, 0.3),
('c017026e-ab4b-451c-a1a9-e80fd4de0798', 'Dollar General Corporation', 'DG', '550e8400-e29b-41d4-a716-446655440004', 0.40, 0.0);