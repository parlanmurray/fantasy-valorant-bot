from fantasyVCT.database import Result

ACS = 0.03
KILLS = 1.5
DEATHS = -1
ASSISTS = 0.5
FK = 1.0
KILLS2 = 2
KILLS3 = 4
KILLS4 = 7
KILLS5 = 10
CLUTCH_V2 = 8
CLUTCH_V3 = 12
CLUTCH_V4 = 16
CLUTCH_V5 = 20

# Role bonus weights (calibrated 2026-03-16, role_calibration_v3.py)
ROLE_IGL_WIN = 8.5
ROLE_DUELIST_FK = 2.0        # total FK weight = 1.0 (base) + 2.0
ROLE_INITIATOR_ASSIST = 1.0  # total assist weight = 0.5 + 1.0
ROLE_CONTROLLER_ASSIST = 0.65
ROLE_CONTROLLER_SURVIVAL = 0.35
ROLE_SENTINEL_DEATH_SAVE = 0.40  # penalty -0.60 instead of -1.0


class PointCalculator:

	@staticmethod
	def get_scoring_info():
		"""
		print storing info.
		similar to __str__ or __repr__ but static
		"""
		rv = "Scoring info:\n"
		rv += f"{'ACS':<20}{ACS}\n"
		rv += f"{'KILLS':<20}{KILLS}\n"
		rv += f"{'DEATHS':<20}{DEATHS}\n"
		rv += f"{'ASSISTS':<20}{ASSISTS}\n"
		rv += f"{'KILLS2':<20}{KILLS2}\n"
		rv += f"{'KILLS3':<20}{KILLS3}\n"
		rv += f"{'KILLS4':<20}{KILLS4}\n"
		rv += f"{'KILLS5':<20}{KILLS5}\n"
		rv += f"{'CLUTCH_V2':<20}{CLUTCH_V2}\n"
		rv += f"{'CLUTCH_V3':<20}{CLUTCH_V3}\n"
		rv += f"{'CLUTCH_V4':<20}{CLUTCH_V4}\n"
		rv += f"{'CLUTCH_V5':<20}{CLUTCH_V5}\n"
		rv += f"{'FK':<20}{FK}\n"
		rv += "\n"
		rv += "Role Bonuses (use !roles for details):\n"
		rv += f"{'IGL':<20}+8.5/win\n"
		rv += f"{'Duelist':<20}+2.0/FK\n"
		rv += f"{'Initiator':<20}+1.0/assist\n"
		rv += f"{'Controller':<20}+0.65/assist  +0.35/survived round\n"
		rv += f"{'Sentinel':<20}+0.40/death (penalty -0.60)\n"
		rv += f"{'Flex':<20}no bonus"
		return rv

	@staticmethod
	def score(player_stats: Result):
		"""
		player_stats retrieved from results table:
		(id, map, game_id, match_id, event_id, player_id, player_acs, player_kills, player_deaths, player_assists,
		player_2k, player_3k, player_4k, player_5k,
		player_clutch_v2, player_clutch_v3, player_clutch_v4, player_clutch_v5, player_fk)
		"""
		rv = player_stats.player_acs * ACS
		rv += player_stats.player_kills * KILLS
		rv += player_stats.player_deaths * DEATHS
		rv += player_stats.player_assists * ASSISTS
		rv += player_stats.player_2k * KILLS2
		rv += player_stats.player_3k * KILLS3
		rv += player_stats.player_4k * KILLS4
		rv += player_stats.player_5k * KILLS5
		rv += player_stats.player_clutch_v2 * CLUTCH_V2
		rv += player_stats.player_clutch_v3 * CLUTCH_V3
		rv += player_stats.player_clutch_v4 * CLUTCH_V4
		rv += player_stats.player_clutch_v5 * CLUTCH_V5
		rv += (player_stats.player_fk or 0) * FK
		return round(rv, 1)

	@staticmethod
	def role_bonus(player_stats: Result, role: str) -> float:
		"""Return the role-specific bonus points for a single result.

		Role bonuses are additive on top of the base score and are only
		applied when the player is assigned to that role slot.
		Flex and Sub slots return 0.
		"""
		r = role.lower()
		if r == 'igl':
			return ROLE_IGL_WIN if player_stats.team_won else 0.0
		elif r == 'duelist':
			return (player_stats.player_fk or 0) * ROLE_DUELIST_FK
		elif r == 'initiator':
			return player_stats.player_assists * ROLE_INITIATOR_ASSIST
		elif r == 'controller':
			survived = (player_stats.rounds_played or 0) - player_stats.player_deaths
			return (player_stats.player_assists * ROLE_CONTROLLER_ASSIST
					+ max(0, survived) * ROLE_CONTROLLER_SURVIVAL)
		elif r == 'sentinel':
			return player_stats.player_deaths * ROLE_SENTINEL_DEATH_SAVE
		return 0.0
