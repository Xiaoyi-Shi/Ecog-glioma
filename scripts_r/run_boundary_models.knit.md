---
title: "Boundary Models Report"
output:
  html_document:
    toc: true
    toc_depth: 2
    df_print: paged
params:
  run_dir: ""
  script_dir: ""
---



## Run Summary


|run_dir                                       | n_features_modeled| n_rows| n_patients|
|:---------------------------------------------|------------------:|------:|----------:|
|F:/uv_env/Ecog-glioma/results/20260526_165202 |                 12|  19810|         18|

## Region Model Results


|feature_name                             |term | estimate| std.error| statistic| p.value| p_fdr|
|:----------------------------------------|:----|--------:|---------:|---------:|-------:|-----:|
|alpha_average_controllability_high_ratio |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_average_controllability_mean       |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_average_controllability_p75        |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_average_controllability_p90        |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_average_controllability_std        |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_clustering_coefficient             |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_eigenvector_centrality             |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_fragility_high_ratio               |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_fragility_mean                     |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_fragility_p75                      |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_fragility_p90                      |NA   |       NA|        NA|        NA|      NA|    NA|
|alpha_fragility_std                      |NA   |       NA|        NA|        NA|      NA|    NA|

## Distance Spline Results


|effect |term                              |   estimate| std.error|  statistic|         df|   p.value|feature_name                             |     p_fdr|
|:------|:---------------------------------|----------:|---------:|----------:|----------:|---------:|:----------------------------------------|---------:|
|fixed  |(Intercept)                       |  0.3063641| 0.1632348|  1.8768307| 127.844526| 0.0628207|alpha_average_controllability_high_ratio | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)1 | -0.0631273| 0.4330887| -0.1457606| 126.728397| 0.8843420|alpha_average_controllability_high_ratio | 0.9031578|
|fixed  |splines::ns(distance_mm, df = 3)2 | -0.6275832| 0.4319790| -1.4528097|  47.394791| 0.1528657|alpha_average_controllability_high_ratio | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.6263931| 0.4174445| -1.5005421|  13.164342| 0.1570724|alpha_average_controllability_high_ratio | 0.3311799|
|fixed  |(Intercept)                       |  0.2545374| 0.1631260|  1.5603733|  66.812402| 0.1233963|alpha_average_controllability_mean       | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)1 | -0.1102950| 0.4237148| -0.2603048| 127.350736| 0.7950491|alpha_average_controllability_mean       | 0.8619372|
|fixed  |splines::ns(distance_mm, df = 3)2 | -0.5716256| 0.4229033| -1.3516698|  27.956457| 0.1873171|alpha_average_controllability_mean       | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.5809711| 0.4004617| -1.4507531|   7.634734| 0.1866604|alpha_average_controllability_mean       | 0.3311799|
|fixed  |(Intercept)                       |  0.2763308| 0.1656280|  1.6683820|  78.804678| 0.0992088|alpha_average_controllability_p75        | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)1 | -0.1904250| 0.4346743| -0.4380867| 125.325423| 0.6620776|alpha_average_controllability_p75        | 0.7978311|
|fixed  |splines::ns(distance_mm, df = 3)2 | -0.5698557| 0.4388076| -1.2986461|  27.289694| 0.2049325|alpha_average_controllability_p75        | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.6394546| 0.4248079| -1.5052795|   7.970899| 0.1708054|alpha_average_controllability_p75        | 0.3311799|
|fixed  |(Intercept)                       |  0.2398452| 0.1617656|  1.4826714|  42.315841| 0.1455716|alpha_average_controllability_p90        | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)1 | -0.1959224| 0.4215802| -0.4647333| 125.609769| 0.6429270|alpha_average_controllability_p90        | 0.7978311|
|fixed  |splines::ns(distance_mm, df = 3)2 | -0.5160113| 0.4268233| -1.2089575|  26.365007| 0.2374099|alpha_average_controllability_p90        | 0.3561148|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.6188143| 0.4123428| -1.5007277|   7.949605| 0.1720549|alpha_average_controllability_p90        | 0.3311799|
|fixed  |(Intercept)                       |  0.2094295| 0.1553566|  1.3480570| 128.386062| 0.1800137|alpha_average_controllability_std        | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)1 | -0.3096025| 0.4086821| -0.7575631| 128.832615| 0.4500960|alpha_average_controllability_std        | 0.6001280|
|fixed  |splines::ns(distance_mm, df = 3)2 | -0.5135930| 0.3998705| -1.2843985|  53.227104| 0.2045648|alpha_average_controllability_std        | 0.3311799|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.5355994| 0.3740601| -1.4318539|  12.511655| 0.1766908|alpha_average_controllability_std        | 0.3311799|
|fixed  |(Intercept)                       | -0.1370127| 0.1539095| -0.8902155| 134.999991| 0.3749339|alpha_clustering_coefficient             | 0.5293184|
|fixed  |splines::ns(distance_mm, df = 3)1 |  0.1119522| 0.4006754|  0.2794087| 134.999999| 0.7803588|alpha_clustering_coefficient             | 0.8619372|
|fixed  |splines::ns(distance_mm, df = 3)2 |  0.1823391| 0.3831295|  0.4759202| 134.999975| 0.6349005|alpha_clustering_coefficient             | 0.7978311|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.5065721| 0.3410002| -1.4855478| 134.999759| 0.1397303|alpha_clustering_coefficient             | 0.3311799|
|fixed  |(Intercept)                       | -0.0003085| 0.1601518| -0.0019264| 135.000000| 0.9984658|alpha_eigenvector_centrality             | 0.9984658|
|fixed  |splines::ns(distance_mm, df = 3)1 |  0.1535032| 0.4169260|  0.3681785| 135.000000| 0.7133168|alpha_eigenvector_centrality             | 0.8152192|
|fixed  |splines::ns(distance_mm, df = 3)2 |  0.0877996| 0.3986685|  0.2202320| 134.999999| 0.8260231|alpha_eigenvector_centrality             | 0.8619372|
|fixed  |splines::ns(distance_mm, df = 3)3 | -0.5630266| 0.3548305| -1.5867480| 134.999992| 0.1149092|alpha_eigenvector_centrality             | 0.3311799|
|fixed  |(Intercept)                       | -0.4012587| 0.1244376| -3.2245778| 102.063922| 0.0016949|alpha_fragility_high_ratio               | 0.0813561|
|fixed  |splines::ns(distance_mm, df = 3)1 | -0.2991874| 0.3713707| -0.8056302|  57.927680| 0.4237509|alpha_fragility_high_ratio               | 0.5811441|

## Moran's I Diagnostics


|feature_name                             |patient |   morans_i| expectation|  variance|   p.value|note                                 |
|:----------------------------------------|:-------|----------:|-----------:|---------:|---------:|:------------------------------------|
|alpha_average_controllability_high_ratio |001     |  0.7490236|  -0.0769231| 0.0714286| 0.0019988|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |002     |  0.1501772|  -0.0526316| 0.0500000| 0.3644130|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |003     |  0.4768165|  -0.0769231| 0.0714286| 0.0382744|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |004     |  0.6899548|  -0.0666667| 0.0625000| 0.0024741|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |005     |  0.5120503|  -0.0714286| 0.0666667| 0.0238334|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |006     |  0.2149701|  -0.0909091| 0.0833333| 0.2893281|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |007     |  0.6847779|  -0.0833333| 0.0769231| 0.0056149|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |008     |  0.6230870|  -0.0555556| 0.0526316| 0.0030951|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |009     |  0.5228793|  -0.0588235| 0.0555556| 0.0135887|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |010     |  0.8234474|  -0.0588235| 0.0555556| 0.0001817|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |011     | -0.0249020|  -0.1250000| 0.1111111| 0.7639530|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |012     |  0.4510532|  -0.0714286| 0.0666667| 0.0430151|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |013     |  0.2980727|  -0.0526316| 0.0500000| 0.1167885|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |014     | -0.1803845|  -0.1250000| 0.1111111| 0.8680362|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |016     |  0.2504886|  -0.0666667| 0.0625000| 0.2045762|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |017     | -0.7122968|  -0.0769231| 0.0714286| 0.0174375|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |018     | -0.1480621|  -0.0666667| 0.0625000| 0.7447410|adjacent_interval_index_graph_approx |
|alpha_average_controllability_high_ratio |019     |  0.4931058|  -0.0526316| 0.0500000| 0.0146624|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |001     |  0.6357817|  -0.0769231| 0.0714286| 0.0076601|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |002     |  0.1187154|  -0.0526316| 0.0500000| 0.4435055|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |003     |  0.5286426|  -0.0769231| 0.0714286| 0.0234624|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |004     |  0.8922379|  -0.0666667| 0.0625000| 0.0001252|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |005     |  0.2049786|  -0.0714286| 0.0666667| 0.2843852|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |006     |  0.4664131|  -0.0909091| 0.0833333| 0.0535300|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |007     |  0.6190314|  -0.0833333| 0.0769231| 0.0113281|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |008     |  0.6197624|  -0.0555556| 0.0526316| 0.0032437|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |009     |  0.5068302|  -0.0588235| 0.0555556| 0.0164011|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |010     |  0.4782094|  -0.0588235| 0.0555556| 0.0227005|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |011     | -0.0594542|  -0.1250000| 0.1111111| 0.8441114|adjacent_interval_index_graph_approx |
|alpha_average_controllability_mean       |012     |  0.2335801|  -0.0714286| 0.0666667| 0.2374862|adjacent_interval_index_graph_approx |
