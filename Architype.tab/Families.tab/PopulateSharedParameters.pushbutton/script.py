public void PopulateSharedParameters()
		{
			var uidoc = this.ActiveUIDocument;
			var doc = this.ActiveUIDocument.Document;
			
			DefinitionFile df = this.Application.OpenSharedParameterFile();
			DefinitionGroups dgs = df.Groups;
							
			Dictionary<string, ExternalDefinition> sharedParameters = new Dictionary<string, ExternalDefinition>();
			
//			string sb = "";
			
			foreach (DefinitionGroup dg in dgs)
            {
                foreach (Definition d in dg.Definitions)
                {
                    if (d != null)
                    {
                        ExternalDefinition ed = d as ExternalDefinition;
                        sharedParameters[ed.Name] = ed;
//                        sb += (string.Format("Parameter {0} with Guid: {1}", ed.Name, ed.GUID.ToString())) + Environment.NewLine;
                    }
                }
            }
			
			Dictionary<string, string> parameters = new Dictionary<string, string>();
			
			parameters["ART_TypeMark"] = " ";	// Family Type
			parameters["Classification.Uniclass.EF.Description"] = "Doors and windows";
			parameters["Classification.Uniclass.EF.Number"] = "EF_25_30";
			parameters["Classification.Uniclass.Pr.Description"] = "Doorsets";
			parameters["Classification.Uniclass.Pr.Number"] = "Pr_30_59_24";
			parameters["Classification.Uniclass.Ss.Description"] = "Door systems";			
			parameters["Classification.Uniclass.Ss.Number"] = "Ss_25_30_20";
			parameters["ClassificationCode"] = "[Uniclass_Pr Classification]Pr_30_59_24:Doorsets";
			parameters["COBie.Type"] = "yes";
			parameters["COBie.Type.AssetType"] = "Fixed";			
			parameters["COBie.Type.Category"] = "Pr_30_59_24 : Doorsets";
			parameters["COBie.Type.CreatedBy"] = "emily.partridge@architype.co.uk";
			parameters["IfcDescription"] = " ";	// Description
			parameters["IfcExportAs"] = "IfcWindowType.DOOR";
			parameters["IfcName"] = " ";	// Family Type			
			
			// 1. Get selection
			// 2. Get unique families
			// 3. for foreach Family
			// 4. Get into the family and 
			// 5. For each parameter in our list, create a new parameter and populate it
			// 6. Save, close
			
			// 1
			var selection = uidoc.Selection.PickObjects(ObjectType.Element, "Pick elements");
			
			// 2
			HashSet<ElementId> families = new HashSet<ElementId>();
			
			foreach(var famRef in selection)
			{
				var fam = doc.GetElement(famRef) as FamilyInstance;
				if(fam == null) continue;
				families.Add(fam.Symbol.Family.Id);				
			}
			
			string log = "";
			
			// 3
			foreach(var id in families)
			{
				Family fam = doc.GetElement(id) as Family;
				if(fam == null) continue;
						
				// 4
				var famDoc = doc.EditFamily(fam);
				
		        using(TransactionGroup tg = new TransactionGroup(famDoc, "weird"))
		        {
		        	tg.Start();
		        	
					// 5 Populate Parameters
					PopulateParameters(famDoc, sharedParameters, parameters);					
				    	
					FamilyTypeSet familyTypes = famDoc.FamilyManager.Types;
			        FamilyTypeSetIterator familyTypesItor = familyTypes.ForwardIterator();
			        familyTypesItor.Reset();			        
						        				        
			        while (familyTypesItor.MoveNext())
			        {
			            FamilyType familyType = familyTypesItor.Current as FamilyType;
			            
			            using(Transaction t = new Transaction(famDoc, "Set FamilyType"))
			            {
			            	t.Start();
				            famDoc.FamilyManager.CurrentType = familyType;			            	
			            	t.Commit();
			            }
			            
					    try{	
				            foreach(KeyValuePair<string, string> pair in parameters)
				            {
								var sParam = pair.Key;
								var vParam = pair.Value;
								
								SetParameter(famDoc, sParam, vParam, familyType);	
				            }
				            log += familyType.Name + Environment.NewLine;
			        	}
					    catch(Exception ex)
					    {					
							TaskDialog.Show("Error", ex.Message);
						}
				    }        
		        	
		        	tg.Assimilate();
		        }
				
				// 6
			    using(Transaction t = new Transaction(famDoc, "Push back"))
			    {
			    	t.Start();		    	
			    	fam = famDoc.LoadFamily(doc, new FamilyOption());
			    	t.Commit();
			    }
				
			    // End for each family
			}
			
			TaskDialog.Show("test", log);
		}
		
		// Popuate all parameters in family		
		private void PopulateParameters(Document doc, Dictionary<string, ExternalDefinition> sharedParameters, Dictionary<string, string> parameters)
		{
	    	try{
		    	using(Transaction ft = new Transaction(doc, "Push parameter"))
				{
					ft.Start();		    							
					
					foreach(var pair in parameters)
					{
						ExternalDefinition sParam = sharedParameters[pair.Key];
						if(doc.FamilyManager.get_Parameter(sParam) != null) continue;	// If we already have that parameter, keep going
						doc.FamilyManager.AddParameter(sParam, BuiltInParameterGroup.PG_DATA, false);
					}	
					
		    		doc.Regenerate();
					ft.Commit();
				}
		    }
		    catch(Exception ex)
		    {					
				TaskDialog.Show("Error", ex.Message);
			}
		}
		// Set a family parameter
		private void SetParameter(Document doc, string pname, string pvalue, FamilyType ftype)
		{			
	    	using(Transaction tp = new Transaction(doc, "Populate parameter"))
			{
				tp.Start();		
				FamilyParameter param = doc.FamilyManager.get_Parameter(pname);
									
	        	if(param == null) return;				            	
	        	
	        	if(pname.Equals("ART_TypeMark") || pname.Equals("IfcName") || pname.Equals("COBie.Type.Name"))
	        	{
	        		doc.FamilyManager.Set(param, ftype.Name);	
	        	}
	        	else if (pname.Equals("IfcDescription"))
	        	{
	        		FamilyParameter dParam = doc.FamilyManager.get_Parameter("Description");
	        		string description = ftype.AsString(dParam);
	        		doc.FamilyManager.Set(param, description);	
	        	}
	        	else if (pname.Equals("COBie.Type"))
	        	{
	        		doc.FamilyManager.Set(param, 1);
	        	}
	        	else{
	        		doc.FamilyManager.Set(param, pvalue);			            		
	        	}
	
				tp.Commit();
	        }	        	
		}
	}
	
	class FamilyOption : IFamilyLoadOptions
	{
		public bool OnFamilyFound(bool familyInUse, out bool overwriteParameterValues)
		{
			overwriteParameterValues = true;
			return true;
		}

		public bool OnSharedFamilyFound(Family sharedFamily,
			bool familyInUse,
			out FamilySource source,
			out bool overwriteParameterValues )
		{
			source = FamilySource.Family;
			overwriteParameterValues = true;
			return true;
		}
	}