import pstats
p = pstats.Stats('profile_stats.prof')
p.sort_stats('tottime').print_stats(10) 