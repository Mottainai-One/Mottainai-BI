-- Semantic guide in the dashboard Data tab. Status refers to source readiness, not a target.
SELECT module, kpi, definition, analysis, source_dataset, status
FROM VALUES
  ('Comercial', 'Receita líquida', 'Soma de net_amount das vendas concluídas', 'Valor realizado; comparar apenas períodos equivalentes', 'ds_period', 'Publicado'),
  ('Comercial', 'Vendas concluídas', 'Contagem de transações COMPLETED', 'Volume de compras; não representa clientes distintos', 'ds_period', 'Publicado'),
  ('Comercial', 'Ticket médio', 'Receita líquida / vendas concluídas', 'Valor por compra; nulo sem vendas', 'ds_period', 'Publicado'),
  ('Comercial', 'Itens por venda', 'Itens vendidos / vendas concluídas', 'Tamanho médio da cesta; não confundir com unidades', 'ds_period', 'Publicado'),
  ('Comercial', 'Variação de receita', '(Receita atual - anterior) / anterior', 'Requer período anterior com receita e mesma duração', 'ds_period', 'Condicional'),
  ('Comercial', 'Lojas e produtos com vendas', 'Contagens distintas no recorte', 'Cobertura observada; não é taxa de conversão', 'ds_sales / ds_product', 'Publicado'),
  ('Comercial', 'Receita por produto', 'Soma do subtotal dos itens conciliados', 'Mostra concentração comercial; não é margem', 'ds_product', 'Publicado'),
  ('Comercial', 'Valor por método', 'Soma dos pagamentos conciliados por venda', 'Uma venda pode usar vários métodos; não somar vendas por método', 'ds_payment', 'Publicado'),
  ('Estoque', 'Unidades disponíveis', 'Quantidade em mãos - reservada', 'Fotografia mais recente por produto e loja', 'ds_inventory', 'Publicado'),
  ('Estoque', 'Produtos com alerta', 'Produto/loja vencido, a vencer ou abaixo do mínimo', 'Contagem de posições que requerem verificação operacional', 'ds_inventory', 'Publicado'),
  ('Estoque', 'Unidades a vencer em 30 dias', 'Soma da quantidade dos lotes com validade próxima', 'Exposição física; não é previsão de perda', 'ds_inventory', 'Publicado'),
  ('Estoque', 'Valor a vencer em 30 dias', 'Quantidade do lote x custo médio conhecido', 'Exposição a custo; fica indisponível quando faltar custo', 'ds_inventory', 'Condicional'),
  ('Estoque', 'Valor do estoque', 'Quantidade em mãos x custo médio conhecido', 'Valor contábil aproximado; não é receita nem margem', 'ds_inventory', 'Condicional'),
  ('Confiabilidade', 'Idade dos dados', 'Horas entre o corte da origem e agora', 'Mostra o atraso da fotografia; não mede acuracidade física', 'ds_reliability', 'Publicado'),
  ('Confiabilidade', 'Validações com falha', 'Regras Silver com invalid_rows maior que zero', 'Zero indica regras aprovadas, não inventário físico correto', 'ds_reliability', 'Publicado'),
  ('Confiabilidade', 'Achados inválidos', 'Soma de invalid_rows nas regras Silver', 'Achados de validação; uma linha pode aparecer em mais de uma regra', 'ds_reliability', 'Publicado'),
  ('Evolutivo', 'Acuracidade de inventário', 'Posições conferidas sem divergência / posições conferidas', 'Exige contagem física e cobertura definida', 'Inventário físico', 'Sem fonte'),
  ('Evolutivo', 'Giro e cobertura de estoque', 'Saídas e estoque médio por SKU/loja em janela suficiente', 'Exige histórico e movimentos válidos', 'Movimentos / snapshots', 'Sem histórico'),
  ('Evolutivo', 'Perda, recuperação e economia atribuível', 'Resultado confirmado, custo histórico e referência causal', 'Valor em risco não equivale a economia realizada', 'Perdas / ações', 'Sem eventos'),
  ('Evolutivo', 'Efetividade dos alertas de IA', 'Alertas avaliados contra resultados observados', 'Exige previsão original, ação e desfecho', 'IA / ações', 'Sem eventos')
AS dictionary(module, kpi, definition, analysis, source_dataset, status);
