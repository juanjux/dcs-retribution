local unitPayloads = {
	["name"] = "MQ-9 Reaper",
	["payloads"] = {
		[1] = {
			["name"] = "CAS",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{88D18A5E-99C8-4B04-B40B-1C02F2018B6E}",
					["num"] = 4,
				},
				[2] = {
					["CLSID"] = "{88D18A5E-99C8-4B04-B40B-1C02F2018B6E}",
					["num"] = 1,
				},
				[3] = {
					["CLSID"] = "AGM114x2_OH_58",
					["num"] = 2,
				},
				[4] = {
					["CLSID"] = "AGM114x2_OH_58",
					["num"] = 3,
				},
			},
			["tasks"] = {
				[1] = 17,
			},
		},
		[2] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{GBU-38}",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "{GBU-38}",
					["num"] = 2,
				},
				[3] = {
					["CLSID"] = "{GBU-38}",
					["num"] = 3,
				},
				[4] = {
					["CLSID"] = "{GBU-38}",
					["num"] = 4,
				},
			},
			["tasks"] = {
				[1] = 31,
			},
		},
	},
	["tasks"] = {
	},
	["unitType"] = "MQ-9 Reaper",
}
return unitPayloads
